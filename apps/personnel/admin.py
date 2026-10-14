from django.contrib import admin, messages
from django.utils import timezone

from apps.core.admin_utils import BaseAdmin

from .models import Competence, Conge, Departement, Personnel, Poste, Presence


@admin.register(Departement)
class DepartementAdmin(BaseAdmin):
    list_display = ("nom", "centre")
    list_filter = ("centre",)
    search_fields = ("nom",)


@admin.register(Poste)
class PosteAdmin(BaseAdmin):
    list_display = ("intitule",)
    search_fields = ("intitule",)


@admin.register(Competence)
class CompetenceAdmin(BaseAdmin):
    search_fields = ("nom",)


class CongeInline(admin.TabularInline):
    model = Conge
    extra = 0
    fields = ("type", "date_debut", "date_fin", "statut")


@admin.register(Personnel)
class PersonnelAdmin(BaseAdmin):
    list_display = ("matricule", "nom", "prenom", "genre", "poste", "departement", "type_contrat", "date_fin", "statut")
    list_filter = ("centre", "statut", "type_contrat", "genre", "departement", "poste")
    search_fields = ("matricule", "nom", "prenom", "email")
    autocomplete_fields = ("utilisateur", "superieur", "departement", "poste")
    filter_horizontal = ("competences",)
    inlines = [CongeInline]
    fieldsets = (
        ("Identité", {"fields": ("centre", "matricule", ("nom", "prenom"), ("genre", "date_naissance"), ("telephone", "email"))}),
        ("Poste", {"fields": (("departement", "poste"), "superieur", "competences", "utilisateur")}),
        ("Contrat", {"fields": (("type_contrat", "statut"), ("date_debut", "date_fin"), "solde_conges")}),
    )


@admin.action(description="Approuver les demandes sélectionnées")
def approuver(modeladmin, request, queryset):
    demandes = queryset.filter(statut=Conge.Statut.DEMANDE)
    for conge in demandes:
        conge.approuver(request.user)
    n = len(demandes)
    messages.success(request, f"{n} demande(s) approuvée(s).")


@admin.action(description="Refuser les demandes sélectionnées")
def refuser(modeladmin, request, queryset):
    n = queryset.filter(statut=Conge.Statut.DEMANDE).update(statut=Conge.Statut.REFUSE, valide_par=request.user)
    messages.warning(request, f"{n} demande(s) refusée(s).")


@admin.register(Conge)
class CongeAdmin(BaseAdmin):
    list_display = ("personnel", "type", "date_debut", "date_fin", "nombre_jours", "statut", "valide_par")
    list_filter = ("statut", "type", "personnel__centre")
    search_fields = ("personnel__nom", "personnel__prenom")
    autocomplete_fields = ("personnel",)
    readonly_fields = ("valide_par",)
    actions = BaseAdmin.actions + [approuver, refuser]
    date_hierarchy = "date_debut"


@admin.register(Presence)
class PresenceAdmin(BaseAdmin):
    list_display = ("personnel", "date", "heure_arrivee", "heure_depart", "teletravail")
    list_filter = ("date", "teletravail", "personnel__centre")
    search_fields = ("personnel__nom", "personnel__prenom")
    autocomplete_fields = ("personnel",)
    date_hierarchy = "date"

    def get_changeform_initial_data(self, request):
        return {"date": timezone.localdate(), "heure_arrivee": timezone.localtime().time().replace(microsecond=0)}
