"""Gestion du personnel : fiches agents, contrats, congés et présences."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F

from apps.core.models import Centre, Genre, Horodatage


class Departement(Horodatage):
    """Unité organisationnelle d'un centre (direction, technique, programmes…)."""

    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name="departements")
    nom = models.CharField("nom", max_length=120)
    description = models.TextField("description", blank=True)

    class Meta:
        verbose_name = "département"
        verbose_name_plural = "départements"
        ordering = ["centre", "nom"]
        constraints = [
            models.UniqueConstraint(fields=["centre", "nom"], name="departement_unique_par_centre"),
        ]

    def __str__(self):
        return self.nom


class Poste(Horodatage):
    """Fonction type d'un UNIPOD (coordinateur, fab manager, ingénieur…)."""

    intitule = models.CharField("intitulé", max_length=120, unique=True)
    description = models.TextField("description / missions", blank=True)

    class Meta:
        verbose_name = "poste"
        verbose_name_plural = "postes"
        ordering = ["intitule"]

    def __str__(self):
        return self.intitule


class Competence(models.Model):
    """Compétence technique ou transversale (impression 3D, IA, gestion de projet…)."""

    nom = models.CharField("nom", max_length=120, unique=True)

    class Meta:
        verbose_name = "compétence"
        verbose_name_plural = "compétences"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Personnel(Horodatage):
    """Fiche d'un membre de l'équipe du centre."""

    class TypeContrat(models.TextChoices):
        CDI = "cdi", "CDI"
        CDD = "cdd", "CDD"
        CONSULTANT = "consultant", "Consultant"
        VOLONTAIRE = "volontaire", "Volontaire (VNU / national)"
        STAGIAIRE = "stagiaire", "Stagiaire"
        DETACHE = "detache", "Détaché (université / État)"

    class Statut(models.TextChoices):
        ACTIF = "actif", "Actif"
        CONGE = "conge", "En congé"
        SUSPENDU = "suspendu", "Suspendu"
        SORTI = "sorti", "Sorti"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="personnel")
    utilisateur = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="compte utilisateur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fiche_personnel",
    )
    matricule = models.CharField("matricule", max_length=30, unique=True)
    nom = models.CharField("nom", max_length=80)
    prenom = models.CharField("prénom", max_length=80)
    genre = models.CharField("genre", max_length=1, choices=Genre.choices)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    departement = models.ForeignKey(
        Departement, verbose_name="département", on_delete=models.SET_NULL, null=True, blank=True
    )
    poste = models.ForeignKey(Poste, on_delete=models.SET_NULL, null=True, blank=True)
    superieur = models.ForeignKey(
        "self", verbose_name="supérieur hiérarchique", on_delete=models.SET_NULL, null=True, blank=True
    )
    type_contrat = models.CharField("type de contrat", max_length=20, choices=TypeContrat.choices)
    date_debut = models.DateField("date de prise de fonction")
    date_fin = models.DateField("date de fin de contrat", null=True, blank=True)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.ACTIF)
    competences = models.ManyToManyField(Competence, verbose_name="compétences", blank=True)
    solde_conges = models.DecimalField("solde de congés (jours)", max_digits=5, decimal_places=1, default=0)

    class Meta:
        verbose_name = "membre du personnel"
        verbose_name_plural = "personnel"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def clean(self):
        if self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin doit suivre la date de début."})


class Conge(Horodatage):
    """Demande de congé / absence avec circuit de validation."""

    class Type(models.TextChoices):
        ANNUEL = "annuel", "Congé annuel"
        MALADIE = "maladie", "Maladie"
        MATERNITE = "maternite", "Maternité / paternité"
        FORMATION = "formation", "Formation / mission"
        EXCEPTIONNEL = "exceptionnel", "Absence exceptionnelle"

    class Statut(models.TextChoices):
        DEMANDE = "demande", "Demandé"
        APPROUVE = "approuve", "Approuvé"
        REFUSE = "refuse", "Refusé"
        ANNULE = "annule", "Annulé"

    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name="conges")
    type = models.CharField("type", max_length=20, choices=Type.choices, default=Type.ANNUEL)
    date_debut = models.DateField("du")
    date_fin = models.DateField("au")
    motif = models.TextField("motif", blank=True)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.DEMANDE)
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="validé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "congé / absence"
        verbose_name_plural = "congés & absences"
        ordering = ["-date_debut"]

    def __str__(self):
        return f"{self.personnel} — {self.get_type_display()} ({self.date_debut} → {self.date_fin})"

    @property
    def nombre_jours(self):
        return (self.date_fin - self.date_debut).days + 1

    def clean(self):
        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            raise ValidationError({"date_fin": "La date de fin doit suivre la date de début."})

    @transaction.atomic
    def approuver(self, utilisateur):
        """Approuve la demande ; un congé annuel est décompté du solde de l'agent."""
        if self.statut != self.Statut.DEMANDE:
            raise ValidationError("Seule une demande en attente peut être approuvée.")
        if self.type == self.Type.ANNUEL:
            Personnel.objects.filter(pk=self.personnel_id).update(
                solde_conges=F("solde_conges") - self.nombre_jours
            )
        self.statut = self.Statut.APPROUVE
        self.valide_par = utilisateur
        self.save(update_fields=["statut", "valide_par", "modifie_le"])


class Presence(models.Model):
    """Pointage journalier du personnel."""

    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name="presences")
    date = models.DateField("date")
    heure_arrivee = models.TimeField("arrivée", null=True, blank=True)
    heure_depart = models.TimeField("départ", null=True, blank=True)
    teletravail = models.BooleanField("télétravail", default=False)
    observation = models.CharField("observation", max_length=255, blank=True)

    class Meta:
        verbose_name = "présence"
        verbose_name_plural = "présences"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["personnel", "date"], name="presence_unique_par_jour"),
        ]

    def __str__(self):
        return f"{self.personnel} — {self.date}"
