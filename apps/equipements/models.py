"""Parc machines : inventaire, habilitations, réservations, maintenance, incidents."""
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import Centre, Espace, Horodatage


class CategorieEquipement(models.Model):
    """Familles d'équipements d'un makerspace UNIPOD standard."""

    class Famille(models.TextChoices):
        FABRICATION_ADDITIVE = "additive", "Fabrication additive (impression 3D)"
        DECOUPE = "decoupe", "Découpe / gravure (laser, vinyle, plasma)"
        USINAGE = "usinage", "Usinage (CNC, tour, fraiseuse)"
        ELECTRONIQUE = "electronique", "Électronique & IoT"
        INFORMATIQUE = "informatique", "Informatique & IA"
        TEXTILE = "textile", "Textile / brodeuse"
        OUTILLAGE = "outillage", "Outillage à main / électroportatif"
        AUDIOVISUEL = "audiovisuel", "Audiovisuel / multimédia"
        MESURE = "mesure", "Mesure & test"
        SECURITE = "securite", "Sécurité / EPI"
        MOBILIER = "mobilier", "Mobilier & infrastructure"

    nom = models.CharField("nom", max_length=120, unique=True)
    famille = models.CharField("famille", max_length=20, choices=Famille.choices)
    description = models.TextField("description", blank=True)

    class Meta:
        verbose_name = "catégorie d'équipement"
        verbose_name_plural = "catégories d'équipement"
        ordering = ["famille", "nom"]

    def __str__(self):
        return self.nom


class Equipement(Horodatage):
    """Machine ou matériel inventorié."""

    class Etat(models.TextChoices):
        OPERATIONNEL = "operationnel", "Opérationnel"
        MAINTENANCE = "maintenance", "En maintenance"
        PANNE = "panne", "En panne"
        HORS_SERVICE = "hors_service", "Hors service / réformé"

    class Risque(models.TextChoices):
        FAIBLE = "faible", "Faible"
        MOYEN = "moyen", "Moyen"
        ELEVE = "eleve", "Élevé"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="equipements")
    espace = models.ForeignKey(Espace, on_delete=models.SET_NULL, null=True, blank=True, related_name="equipements")
    categorie = models.ForeignKey(CategorieEquipement, verbose_name="catégorie", on_delete=models.PROTECT)
    code_inventaire = models.CharField("code inventaire", max_length=40, unique=True)
    nom = models.CharField("désignation", max_length=150)
    marque = models.CharField("marque", max_length=80, blank=True)
    modele = models.CharField("modèle", max_length=80, blank=True)
    numero_serie = models.CharField("n° de série", max_length=80, blank=True)
    date_acquisition = models.DateField("date d'acquisition", null=True, blank=True)
    valeur_acquisition = models.DecimalField(
        "valeur d'acquisition (FCFA)", max_digits=14, decimal_places=0, null=True, blank=True
    )
    source_financement = models.CharField("source de financement", max_length=150, blank=True)
    fournisseur = models.ForeignKey(
        "stocks.Fournisseur", on_delete=models.SET_NULL, null=True, blank=True, related_name="equipements"
    )
    fin_garantie = models.DateField("fin de garantie", null=True, blank=True)
    etat = models.CharField("état", max_length=20, choices=Etat.choices, default=Etat.OPERATIONNEL)
    niveau_risque = models.CharField("niveau de risque", max_length=10, choices=Risque.choices, default=Risque.FAIBLE)
    habilitation_requise = models.BooleanField(
        "habilitation requise", default=False, help_text="L'usager doit être formé avant toute réservation."
    )
    reservable = models.BooleanField("réservable par les usagers", default=True)
    tarif_horaire = models.DecimalField("tarif horaire (FCFA)", max_digits=10, decimal_places=0, default=0)
    periodicite_maintenance = models.PositiveIntegerField(
        "périodicité de maintenance préventive (jours)", null=True, blank=True
    )
    consignes_securite = models.TextField("consignes de sécurité", blank=True)
    responsable = models.ForeignKey(
        "personnel.Personnel", on_delete=models.SET_NULL, null=True, blank=True, related_name="equipements_suivis"
    )

    class Meta:
        verbose_name = "équipement"
        verbose_name_plural = "équipements"
        ordering = ["code_inventaire"]

    def __str__(self):
        return f"{self.code_inventaire} — {self.nom}"

    @property
    def disponible(self):
        return self.etat == self.Etat.OPERATIONNEL

    @property
    def derniere_maintenance(self):
        m = self.maintenances.filter(statut=Maintenance.Statut.TERMINEE).order_by("-date_realisation").first()
        return m.date_realisation if m else None

    @property
    def prochaine_maintenance(self):
        """Date théorique de la prochaine maintenance préventive."""
        if not self.periodicite_maintenance:
            return None
        base = self.derniere_maintenance or self.date_acquisition
        if not base:
            return None
        return base + timedelta(days=self.periodicite_maintenance)

    @property
    def heures_utilisation(self):
        total = timedelta()
        for r in self.reservations.filter(statut=Reservation.Statut.TERMINEE):
            total += r.fin - r.debut
        return round(total.total_seconds() / 3600, 1)


class Habilitation(Horodatage):
    """Autorisation d'un usager à utiliser une catégorie de machines (après formation)."""

    usager = models.ForeignKey("usagers.Usager", on_delete=models.CASCADE, related_name="habilitations")
    categorie = models.ForeignKey(CategorieEquipement, verbose_name="catégorie", on_delete=models.CASCADE)
    date_obtention = models.DateField("date d'obtention", default=timezone.localdate)
    date_expiration = models.DateField("date d'expiration", null=True, blank=True)
    formateur = models.ForeignKey("personnel.Personnel", on_delete=models.SET_NULL, null=True, blank=True)
    observation = models.CharField("observation", max_length=255, blank=True)

    class Meta:
        verbose_name = "habilitation"
        verbose_name_plural = "habilitations"
        constraints = [
            models.UniqueConstraint(fields=["usager", "categorie"], name="habilitation_unique"),
        ]

    def __str__(self):
        return f"{self.usager} → {self.categorie}"

    @property
    def valide(self):
        return self.date_expiration is None or self.date_expiration >= timezone.localdate()


class Reservation(Horodatage):
    """Créneau de réservation d'une machine."""

    class Statut(models.TextChoices):
        DEMANDEE = "demandee", "Demandée"
        CONFIRMEE = "confirmee", "Confirmée"
        EN_COURS = "en_cours", "En cours"
        TERMINEE = "terminee", "Terminée"
        ANNULEE = "annulee", "Annulée"

    STATUTS_ACTIFS = (Statut.DEMANDEE, Statut.CONFIRMEE, Statut.EN_COURS)

    equipement = models.ForeignKey(Equipement, on_delete=models.CASCADE, related_name="reservations")
    usager = models.ForeignKey("usagers.Usager", on_delete=models.CASCADE, related_name="reservations")
    projet = models.ForeignKey(
        "programmes.Projet", on_delete=models.SET_NULL, null=True, blank=True, related_name="reservations"
    )
    debut = models.DateTimeField("début")
    fin = models.DateTimeField("fin")
    objet = models.CharField("objet / travail prévu", max_length=255, blank=True)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.DEMANDEE)

    class Meta:
        verbose_name = "réservation"
        verbose_name_plural = "réservations"
        ordering = ["-debut"]

    def __str__(self):
        return f"{self.equipement.nom} — {self.usager} ({self.debut:%d/%m %H:%M})"

    @property
    def duree_heures(self):
        return round((self.fin - self.debut).total_seconds() / 3600, 2)

    def clean(self):
        errors = {}
        if self.debut and self.fin and self.fin <= self.debut:
            errors["fin"] = "La fin doit être postérieure au début."
        if self.equipement_id and self.statut in self.STATUTS_ACTIFS:
            eq = self.equipement
            if not eq.reservable:
                errors["equipement"] = "Cet équipement n'est pas réservable."
            elif not eq.disponible:
                errors["equipement"] = f"Équipement indisponible ({eq.get_etat_display()})."
            if self.debut and self.fin and "fin" not in errors:
                chevauchement = Reservation.objects.filter(
                    equipement=eq, statut__in=self.STATUTS_ACTIFS, debut__lt=self.fin, fin__gt=self.debut
                ).exclude(pk=self.pk)
                if chevauchement.exists():
                    errors["debut"] = "Ce créneau chevauche une réservation existante."
            if eq.habilitation_requise and self.usager_id:
                hab = Habilitation.objects.filter(usager_id=self.usager_id, categorie_id=eq.categorie_id).first()
                if not hab or not hab.valide:
                    errors["usager"] = "L'usager ne dispose pas d'une habilitation valide pour cette machine."
        if errors:
            raise ValidationError(errors)


class Maintenance(Horodatage):
    """Intervention de maintenance préventive ou corrective."""

    class Type(models.TextChoices):
        PREVENTIVE = "preventive", "Préventive"
        CORRECTIVE = "corrective", "Corrective"
        CALIBRATION = "calibration", "Calibration / réglage"

    class Statut(models.TextChoices):
        PLANIFIEE = "planifiee", "Planifiée"
        EN_COURS = "en_cours", "En cours"
        TERMINEE = "terminee", "Terminée"
        ANNULEE = "annulee", "Annulée"

    equipement = models.ForeignKey(Equipement, on_delete=models.CASCADE, related_name="maintenances")
    type = models.CharField("type", max_length=20, choices=Type.choices)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.PLANIFIEE)
    date_planifiee = models.DateField("date planifiée")
    date_realisation = models.DateField("date de réalisation", null=True, blank=True)
    intervenant = models.ForeignKey("personnel.Personnel", on_delete=models.SET_NULL, null=True, blank=True)
    prestataire_externe = models.CharField("prestataire externe", max_length=150, blank=True)
    description = models.TextField("travaux / constat")
    cout = models.DecimalField("coût (FCFA)", max_digits=12, decimal_places=0, default=0)
    incident = models.ForeignKey(
        "Incident", on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenances"
    )

    class Meta:
        verbose_name = "maintenance"
        verbose_name_plural = "maintenances"
        ordering = ["-date_planifiee"]

    def __str__(self):
        return f"{self.get_type_display()} — {self.equipement} ({self.date_planifiee})"

    def clean(self):
        if self.statut == self.Statut.TERMINEE and not self.date_realisation:
            raise ValidationError({"date_realisation": "Indiquez la date de réalisation."})


class Incident(Horodatage):
    """Panne, casse ou incident de sécurité signalé sur un équipement."""

    class Gravite(models.TextChoices):
        MINEURE = "mineure", "Mineure"
        MAJEURE = "majeure", "Majeure (machine arrêtée)"
        SECURITE = "securite", "Incident de sécurité / accident"

    class Statut(models.TextChoices):
        OUVERT = "ouvert", "Ouvert"
        EN_TRAITEMENT = "en_traitement", "En traitement"
        RESOLU = "resolu", "Résolu"

    equipement = models.ForeignKey(Equipement, on_delete=models.CASCADE, related_name="incidents")
    date = models.DateTimeField("date", default=timezone.now)
    gravite = models.CharField("gravité", max_length=20, choices=Gravite.choices)
    description = models.TextField("description")
    signale_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    usager_implique = models.ForeignKey("usagers.Usager", on_delete=models.SET_NULL, null=True, blank=True)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.OUVERT)
    date_resolution = models.DateTimeField("date de résolution", null=True, blank=True)

    class Meta:
        verbose_name = "incident"
        verbose_name_plural = "incidents"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_gravite_display()} — {self.equipement} ({self.date:%d/%m/%Y})"

    def save(self, *args, **kwargs):
        # Un incident majeur ouvert met automatiquement la machine en panne.
        creation = self._state.adding
        super().save(*args, **kwargs)
        if creation and self.gravite != self.Gravite.MINEURE and self.statut != self.Statut.RESOLU:
            Equipement.objects.filter(pk=self.equipement_id, etat=Equipement.Etat.OPERATIONNEL).update(
                etat=Equipement.Etat.PANNE
            )
