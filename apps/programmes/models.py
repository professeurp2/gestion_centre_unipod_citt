"""Programmes UNIPOD : formations, événements, incubation et projets d'innovation.

Les types d'activités reprennent l'offre standard des UNIPOD (PNUD / initiative
timbuktoo) : formations techniques, bootcamps, hackathons, programmes
d'incubation et d'accélération, défis d'innovation.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import Centre, Espace, Horodatage, Partenaire


class ODD(models.Model):
    """Objectifs de développement durable (17 ODD des Nations unies)."""

    numero = models.PositiveSmallIntegerField("numéro", unique=True)
    intitule = models.CharField("intitulé", max_length=150)

    class Meta:
        verbose_name = "ODD"
        verbose_name_plural = "ODD"
        ordering = ["numero"]

    def __str__(self):
        return f"ODD {self.numero} — {self.intitule}"


class Programme(Horodatage):
    class Type(models.TextChoices):
        FORMATION = "formation", "Formation technique"
        BOOTCAMP = "bootcamp", "Bootcamp"
        HACKATHON = "hackathon", "Hackathon / défi d'innovation"
        INCUBATION = "incubation", "Incubation"
        ACCELERATION = "acceleration", "Accélération"
        SENSIBILISATION = "sensibilisation", "Sensibilisation / événement"
        RECHERCHE = "recherche", "Recherche appliquée"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="programmes")
    titre = models.CharField("titre", max_length=200)
    type = models.CharField("type", max_length=20, choices=Type.choices)
    description = models.TextField("description", blank=True)
    date_debut = models.DateField("date de début")
    date_fin = models.DateField("date de fin", null=True, blank=True)
    responsable = models.ForeignKey("personnel.Personnel", on_delete=models.SET_NULL, null=True, blank=True)
    partenaires = models.ManyToManyField(Partenaire, blank=True, related_name="programmes")
    odd = models.ManyToManyField(ODD, verbose_name="ODD ciblés", blank=True)
    budget = models.DecimalField("budget (FCFA)", max_digits=14, decimal_places=0, default=0)

    class Meta:
        verbose_name = "programme"
        verbose_name_plural = "programmes"
        ordering = ["-date_debut"]

    def __str__(self):
        return self.titre


class Session(Horodatage):
    """Séance concrète d'un programme (atelier, module, journée de hackathon…)."""

    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name="sessions")
    titre = models.CharField("titre", max_length=200)
    debut = models.DateTimeField("début")
    fin = models.DateTimeField("fin")
    espace = models.ForeignKey(Espace, on_delete=models.SET_NULL, null=True, blank=True)
    formateurs = models.ManyToManyField("personnel.Personnel", blank=True, related_name="sessions_animees")
    intervenant_externe = models.CharField("intervenant externe", max_length=150, blank=True)
    capacite = models.PositiveIntegerField("places", default=20)
    en_ligne = models.BooleanField("en ligne", default=False)

    class Meta:
        verbose_name = "session"
        verbose_name_plural = "sessions"
        ordering = ["-debut"]

    def __str__(self):
        return f"{self.titre} ({self.debut:%d/%m/%Y})"

    @property
    def places_restantes(self):
        return self.capacite - self.inscriptions.exclude(statut=Inscription.Statut.ANNULEE).count()

    def clean(self):
        if self.debut and self.fin and self.fin <= self.debut:
            raise ValidationError({"fin": "La fin doit être postérieure au début."})


class Inscription(Horodatage):
    class Statut(models.TextChoices):
        INSCRIT = "inscrit", "Inscrit·e"
        PRESENT = "present", "Présent·e"
        ABSENT = "absent", "Absent·e"
        ANNULEE = "annulee", "Annulée"

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="inscriptions")
    usager = models.ForeignKey("usagers.Usager", on_delete=models.CASCADE, related_name="inscriptions")
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.INSCRIT)
    certificat_delivre = models.BooleanField("certificat délivré", default=False)
    evaluation = models.PositiveSmallIntegerField(
        "satisfaction (1-5)", null=True, blank=True, choices=[(i, str(i)) for i in range(1, 6)]
    )

    class Meta:
        verbose_name = "inscription"
        verbose_name_plural = "inscriptions"
        constraints = [
            models.UniqueConstraint(fields=["session", "usager"], name="inscription_unique"),
        ]

    def __str__(self):
        return f"{self.usager} — {self.session}"

    def clean(self):
        if self.pk is None and self.session_id and self.session.places_restantes <= 0:
            raise ValidationError("La session est complète.")


class Projet(Horodatage):
    """Projet d'innovation / prototype / startup accompagné par le centre."""

    class Stade(models.TextChoices):
        IDEATION = "ideation", "Idéation"
        PROTOTYPE = "prototype", "Prototype"
        MVP = "mvp", "Produit minimum viable (MVP)"
        PILOTE = "pilote", "Pilote / test terrain"
        STARTUP = "startup", "Startup créée"
        COMMERCIALISATION = "commercialisation", "Commercialisation / passage à l'échelle"

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        SUSPENDU = "suspendu", "Suspendu"
        TERMINE = "termine", "Terminé"
        ABANDONNE = "abandonne", "Abandonné"

    class Domaine(models.TextChoices):
        AGRITECH = "agritech", "Agriculture / agro-industrie"
        SANTE = "sante", "Santé"
        ENERGIE = "energie", "Énergie / climat"
        EDUCATION = "education", "Éducation"
        FINTECH = "fintech", "Finance / fintech"
        EAU = "eau", "Eau & assainissement"
        INDUSTRIE = "industrie", "Industrie / fabrication"
        NUMERIQUE = "numerique", "Numérique / IA"
        AUTRE = "autre", "Autre"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="projets")
    titre = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    porteur = models.ForeignKey("usagers.Usager", on_delete=models.PROTECT, related_name="projets_portes")
    membres = models.ManyToManyField("usagers.Usager", blank=True, related_name="projets")
    programme = models.ForeignKey(Programme, on_delete=models.SET_NULL, null=True, blank=True, related_name="projets")
    mentor = models.ForeignKey("personnel.Personnel", on_delete=models.SET_NULL, null=True, blank=True)
    domaine = models.CharField("domaine", max_length=20, choices=Domaine.choices, default=Domaine.AUTRE)
    odd = models.ManyToManyField(ODD, verbose_name="ODD", blank=True)
    stade = models.CharField("stade de maturité", max_length=20, choices=Stade.choices, default=Stade.IDEATION)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    date_debut = models.DateField("date de début", default=timezone.localdate)
    propriete_intellectuelle = models.CharField("propriété intellectuelle (brevet, marque…)", max_length=200, blank=True)
    emplois_crees = models.PositiveIntegerField("emplois créés", default=0)
    fonds_mobilises = models.DecimalField("fonds mobilisés (FCFA)", max_digits=14, decimal_places=0, default=0)

    class Meta:
        verbose_name = "projet d'innovation"
        verbose_name_plural = "projets d'innovation"
        ordering = ["-date_debut"]

    def __str__(self):
        return self.titre


class JalonProjet(Horodatage):
    """Étape de suivi d'un projet (passage de stade, prix gagné, levée…)."""

    projet = models.ForeignKey(Projet, on_delete=models.CASCADE, related_name="jalons")
    date = models.DateField("date", default=timezone.localdate)
    titre = models.CharField("titre", max_length=200)
    description = models.TextField("description", blank=True)
    stade_atteint = models.CharField("stade atteint", max_length=20, choices=Projet.Stade.choices, blank=True)

    class Meta:
        verbose_name = "jalon"
        verbose_name_plural = "jalons"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.projet} — {self.titre}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.stade_atteint:
            Projet.objects.filter(pk=self.projet_id).update(stade=self.stade_atteint)
