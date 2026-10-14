from django.contrib import admin, messages
from django.utils import timezone

from apps.core.admin_utils import BaseAdmin

from .models import CategorieEquipement, Equipement, Habilitation, Incident, Maintenance, Reservation


@admin.register(CategorieEquipement)
class CategorieEquipementAdmin(BaseAdmin):
    list_display = ("nom", "famille")
    list_filter = ("famille",)
    search_fields = ("nom",)


class MaintenanceInline(admin.TabularInline):
    model = Maintenance
    extra = 0
    fields = ("type", "statut", "date_planifiee", "date_realisation", "intervenant", "cout")
    show_change_link = True


class IncidentInline(admin.TabularInline):
    model = Incident
    extra = 0
    fields = ("date", "gravite", "statut", "description")
    show_change_link = True


@admin.register(Equipement)
class EquipementAdmin(BaseAdmin):
    list_display = (
        "code_inventaire", "nom", "categorie", "espace", "etat", "niveau_risque",
        "habilitation_requise", "prochaine_maintenance",
    )
    list_filter = ("centre", "etat", "categorie__famille", "categorie", "espace", "niveau_risque", "habilitation_requise")
    search_fields = ("code_inventaire", "nom", "marque", "modele", "numero_serie")
    autocomplete_fields = ("categorie", "fournisseur", "responsable", "espace")
    readonly_fields = ("derniere_maintenance", "prochaine_maintenance", "heures_utilisation")
    inlines = [MaintenanceInline, IncidentInline]
    fieldsets = (
        ("Identification", {"fields": ("centre", "code_inventaire", "nom", "categorie", ("marque", "modele"), "numero_serie")}),
        ("Localisation & responsabilité", {"fields": ("espace", "responsable")}),
        ("Acquisition", {"fields": (("date_acquisition", "valeur_acquisition"), "source_financement", "fournisseur", "fin_garantie")}),
        ("Exploitation", {"fields": (
            ("etat", "niveau_risque"), ("reservable", "habilitation_requise"), "tarif_horaire",
            "consignes_securite", "heures_utilisation",
        )}),
        ("Maintenance", {"fields": ("periodicite_maintenance", "derniere_maintenance", "prochaine_maintenance")}),
    )


@admin.register(Habilitation)
class HabilitationAdmin(BaseAdmin):
    list_display = ("usager", "categorie", "date_obtention", "date_expiration", "valide", "formateur")
    list_filter = ("categorie",)
    search_fields = ("usager__nom", "usager__prenom", "usager__numero_carte")
    autocomplete_fields = ("usager", "categorie", "formateur")

    @admin.display(boolean=True, description="valide")
    def valide(self, obj):
        return obj.valide


@admin.action(description="Confirmer les réservations")
def confirmer(modeladmin, request, queryset):
    n = queryset.filter(statut=Reservation.Statut.DEMANDEE).update(statut=Reservation.Statut.CONFIRMEE)
    messages.success(request, f"{n} réservation(s) confirmée(s).")


@admin.action(description="Marquer comme terminées")
def terminer(modeladmin, request, queryset):
    n = queryset.filter(statut__in=Reservation.STATUTS_ACTIFS).update(statut=Reservation.Statut.TERMINEE)
    messages.success(request, f"{n} réservation(s) terminée(s).")


@admin.register(Reservation)
class ReservationAdmin(BaseAdmin):
    list_display = ("equipement", "usager", "debut", "fin", "duree_heures", "statut", "projet")
    list_filter = ("statut", "equipement__centre", "equipement__categorie")
    search_fields = ("equipement__nom", "equipement__code_inventaire", "usager__nom", "usager__prenom")
    autocomplete_fields = ("equipement", "usager", "projet")
    date_hierarchy = "debut"
    actions = BaseAdmin.actions + [confirmer, terminer]


@admin.register(Maintenance)
class MaintenanceAdmin(BaseAdmin):
    list_display = ("equipement", "type", "statut", "date_planifiee", "date_realisation", "intervenant", "cout")
    list_filter = ("statut", "type", "equipement__centre")
    search_fields = ("equipement__nom", "equipement__code_inventaire", "description")
    autocomplete_fields = ("equipement", "intervenant", "incident")
    date_hierarchy = "date_planifiee"


@admin.action(description="Marquer comme résolus")
def resoudre(modeladmin, request, queryset):
    n = queryset.exclude(statut=Incident.Statut.RESOLU).update(
        statut=Incident.Statut.RESOLU, date_resolution=timezone.now()
    )
    messages.success(request, f"{n} incident(s) résolu(s).")


@admin.register(Incident)
class IncidentAdmin(BaseAdmin):
    list_display = ("equipement", "date", "gravite", "statut", "signale_par")
    list_filter = ("statut", "gravite", "equipement__centre")
    search_fields = ("equipement__nom", "equipement__code_inventaire", "description")
    autocomplete_fields = ("equipement", "usager_implique")
    readonly_fields = ("signale_par",)
    actions = BaseAdmin.actions + [resoudre]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.signale_par = request.user
        super().save_model(request, obj, form, change)
