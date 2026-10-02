"""Usagers (bénéficiaires) du centre et suivi de la fréquentation."""
from django.db import models
from django.utils import timezone

from apps.core.models import Centre, Espace, Genre, Horodatage


class Usager(Horodatage):
    """Bénéficiaire inscrit : étudiant, enseignant-chercheur, startup, public…"""

    class Categorie(models.TextChoices):
        ETUDIANT = "etudiant", "Étudiant·e"
        ENSEIGNANT = "enseignant", "Enseignant·e / chercheur·e"
        ENTREPRENEUR = "entrepreneur", "Entrepreneur·e / startup"
        ALUMNI = "alumni", "Diplômé·e / alumni"
        ARTISAN = "artisan", "Artisan·e / innovateur·rice local·e"
        EXTERNE = "externe", "Public externe / entreprise"

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"
        INACTIF = "inactif", "Inactif"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="usagers")
    numero_carte = models.CharField("n° de carte membre", max_length=30, unique=True)
    nom = models.CharField("nom", max_length=80)
    prenom = models.CharField("prénom", max_length=80)
    genre = models.CharField("genre", max_length=1, choices=Genre.choices)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    situation_handicap = models.BooleanField("en situation de handicap", default=False)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    categorie = models.CharField("catégorie", max_length=20, choices=Categorie.choices)
    etablissement = models.CharField("université / établissement / structure", max_length=200, blank=True)
    filiere = models.CharField("filière / domaine", max_length=150, blank=True)
    date_adhesion = models.DateField("date d'adhésion", default=timezone.localdate)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    consentement_donnees = models.BooleanField("consentement au traitement des données", default=False)

    class Meta:
        verbose_name = "usager"
        verbose_name_plural = "usagers"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.numero_carte})"

    @property
    def age(self):
        if not self.date_naissance:
            return None
        today = timezone.localdate()
        d = self.date_naissance
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))


class Visite(models.Model):
    """Entrée / sortie d'un usager (registre de fréquentation)."""

    class Motif(models.TextChoices):
        PROTOTYPAGE = "prototypage", "Prototypage / fabrication"
        FORMATION = "formation", "Formation / atelier"
        COWORKING = "coworking", "Coworking"
        MENTORAT = "mentorat", "Mentorat / coaching"
        EVENEMENT = "evenement", "Événement"
        VISITE = "visite", "Visite / découverte"

    usager = models.ForeignKey(Usager, on_delete=models.CASCADE, related_name="visites")
    espace = models.ForeignKey(Espace, on_delete=models.SET_NULL, null=True, blank=True)
    motif = models.CharField("motif", max_length=20, choices=Motif.choices)
    arrivee = models.DateTimeField("arrivée", default=timezone.now)
    depart = models.DateTimeField("départ", null=True, blank=True)

    class Meta:
        verbose_name = "visite"
        verbose_name_plural = "registre des visites"
        ordering = ["-arrivee"]

    def __str__(self):
        return f"{self.usager} — {self.arrivee:%d/%m/%Y %H:%M}"

    @property
    def duree_heures(self):
        if not self.depart:
            return None
        return round((self.depart - self.arrivee).total_seconds() / 3600, 2)
