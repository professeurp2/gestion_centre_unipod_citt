from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core import referentiels as R
from apps.core.models import Centre, Espace
from apps.equipements.models import CategorieEquipement
from apps.personnel.models import Departement, Poste
from apps.programmes.models import ODD
from apps.stocks.models import CategorieArticle


class Command(BaseCommand):
    help = "Initialise un centre UNIPOD avec les référentiels standards et les rôles (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--code", default="unipod-mali")
        parser.add_argument("--nom", default="UNIPOD Mali")
        parser.add_argument("--ville", default="Bamako")
        parser.add_argument("--pays", default="Mali")
        parser.add_argument("--universite", default="")

    @transaction.atomic
    def handle(self, *args, **o):
        centre, cree = Centre.objects.get_or_create(
            code=o["code"],
            defaults={"nom": o["nom"], "ville": o["ville"], "pays": o["pays"], "universite_hote": o["universite"]},
        )
        self.stdout.write(f"Centre {'créé' if cree else 'existant'} : {centre}")

        for nom, type_, capacite in R.ESPACES:
            Espace.objects.get_or_create(centre=centre, nom=nom, defaults={"type": type_, "capacite": capacite})
        for nom in R.DEPARTEMENTS:
            Departement.objects.get_or_create(centre=centre, nom=nom)
        for intitule in R.POSTES:
            Poste.objects.get_or_create(intitule=intitule)
        for nom, famille in R.CATEGORIES_EQUIPEMENT:
            CategorieEquipement.objects.get_or_create(nom=nom, defaults={"famille": famille})
        for nom in R.CATEGORIES_ARTICLE:
            CategorieArticle.objects.get_or_create(nom=nom)
        for numero, intitule in R.ODD:
            ODD.objects.update_or_create(numero=numero, defaults={"intitule": intitule})

        for nom_role, droits in R.ROLES.items():
            groupe, _ = Group.objects.get_or_create(name=nom_role)
            perms = []
            for app, actions in droits.items():
                qs = Permission.objects.filter(content_type__app_label=app)
                perms += [p for p in qs if p.codename.split("_", 1)[0] in actions]
            groupe.permissions.set(perms)

        self.stdout.write(self.style.SUCCESS("Référentiels et rôles UNIPOD initialisés."))
