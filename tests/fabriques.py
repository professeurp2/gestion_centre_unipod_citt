"""Petites fabriques d'objets pour les tests."""
from datetime import date, timedelta

from django.utils import timezone

from apps.core.models import Centre
from apps.equipements.models import CategorieEquipement, Equipement
from apps.personnel.models import Personnel
from apps.stocks.models import Article, CategorieArticle
from apps.usagers.models import Usager

_compteur = iter(range(1, 10**6))


def centre(code="test"):
    return Centre.objects.get_or_create(code=code, defaults={"nom": f"Centre {code}"})[0]


def usager(c=None, genre="F", **kw):
    n = next(_compteur)
    return Usager.objects.create(
        centre=c or centre(), numero_carte=f"U{n}", nom=f"Nom{n}", prenom="Test", genre=genre,
        categorie="etudiant", **kw,
    )


def personnel(c=None, **kw):
    n = next(_compteur)
    valeurs = dict(centre=c or centre(), matricule=f"P{n}", nom=f"Agent{n}", prenom="Test", genre="H",
                   type_contrat="cdi", date_debut=date(2024, 1, 1))
    valeurs.update(kw)
    return Personnel.objects.create(**valeurs)


def equipement(c=None, habilitation=False, **kw):
    n = next(_compteur)
    cat = CategorieEquipement.objects.get_or_create(nom="Imprimante 3D", defaults={"famille": "additive"})[0]
    return Equipement.objects.create(
        centre=c or centre(), code_inventaire=f"EQ{n}", nom=f"Machine {n}", categorie=cat,
        habilitation_requise=habilitation, **kw,
    )


def article(c=None, **kw):
    n = next(_compteur)
    cat = CategorieArticle.objects.get_or_create(nom="Filament")[0]
    valeurs = dict(centre=c or centre(), reference=f"A{n}", designation=f"Article {n}", categorie=cat,
                   prix_unitaire=1000, seuil_alerte=2)
    valeurs.update(kw)
    return Article.objects.create(**valeurs)


def creneau(jours=1, heures=2, heure=9):
    debut = (timezone.now() + timedelta(days=jours)).replace(hour=heure, minute=0, second=0, microsecond=0)
    return debut, debut + timedelta(hours=heures)
