"""Modèles transversaux : centres UNIPOD, espaces et classes de base.

La plateforme est conçue « multi-centres » : chaque entité opérationnelle est
rattachée à un ``Centre``. Le centre UNIPOD Mali est le premier, mais d'autres
pods (ou antennes) peuvent être ajoutés sans modifier le code.
"""
from django.conf import settings
from django.db import models


class Horodatage(models.Model):
    """Ajoute les dates de création / modification à un modèle."""

    cree_le = models.DateTimeField("créé le", auto_now_add=True)
    modifie_le = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class Tracabilite(Horodatage):
    """Horodatage + auteur de la création."""

    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="créé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True


class Genre(models.TextChoices):
    """Désagrégation par genre exigée par les rapports PNUD / UNIPOD."""

    FEMME = "F", "Femme"
    HOMME = "H", "Homme"
    AUTRE = "A", "Autre / non précisé"


class Centre(Horodatage):
    """Un centre UNIPOD (University Innovation Pod)."""

    code = models.SlugField("code", max_length=20, unique=True)
    nom = models.CharField("nom", max_length=150)
    pays = models.CharField("pays", max_length=80, default="Mali")
    ville = models.CharField("ville", max_length=80, default="Bamako")
    universite_hote = models.CharField("université hôte", max_length=200, blank=True)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    date_ouverture = models.DateField("date d'ouverture", null=True, blank=True)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "centre"
        verbose_name_plural = "centres"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Espace(Horodatage):
    """Zone physique d'un centre, selon le découpage standard UNIPOD."""

    class Type(models.TextChoices):
        MAKERSPACE = "makerspace", "Makerspace / Fab Lab"
        ELECTRONIQUE = "electronique", "Laboratoire électronique & IoT"
        NUMERIQUE = "numerique", "Laboratoire numérique (IA, logiciel, données)"
        DESIGN = "design", "Studio design / créatif"
        FORMATION = "formation", "Salle de formation"
        COWORKING = "coworking", "Espace coworking / idéation"
        INCUBATION = "incubation", "Espace incubation / accélération"
        REUNION = "reunion", "Salle de réunion"
        STOCKAGE = "stockage", "Magasin / stockage"
        AUTRE = "autre", "Autre"

    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name="espaces")
    nom = models.CharField("nom", max_length=120)
    type = models.CharField("type", max_length=20, choices=Type.choices, default=Type.AUTRE)
    capacite = models.PositiveIntegerField("capacité (personnes)", default=0)
    responsable = models.ForeignKey(
        "personnel.Personnel",
        verbose_name="responsable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="espaces_geres",
    )
    description = models.TextField("description", blank=True)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "espace"
        verbose_name_plural = "espaces"
        ordering = ["centre", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["centre", "nom"], name="espace_unique_par_centre"),
        ]

    def __str__(self):
        return f"{self.nom} ({self.centre.code})"


class Partenaire(Horodatage):
    """Partenaires de l'écosystème (PNUD, université, ministères, entreprises…)."""

    class Type(models.TextChoices):
        BAILLEUR = "bailleur", "Bailleur / agence"
        ACADEMIQUE = "academique", "Académique / recherche"
        PUBLIC = "public", "Institution publique"
        PRIVE = "prive", "Secteur privé"
        ONG = "ong", "ONG / société civile"
        INCUBATEUR = "incubateur", "Incubateur / hub"

    nom = models.CharField("nom", max_length=200, unique=True)
    type = models.CharField("type", max_length=20, choices=Type.choices)
    contact = models.CharField("personne de contact", max_length=150, blank=True)
    email = models.EmailField("e-mail", blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    site_web = models.URLField("site web", blank=True)
    centres = models.ManyToManyField(Centre, verbose_name="centres", blank=True, related_name="partenaires")

    class Meta:
        verbose_name = "partenaire"
        verbose_name_plural = "partenaires"
        ordering = ["nom"]

    def __str__(self):
        return self.nom
