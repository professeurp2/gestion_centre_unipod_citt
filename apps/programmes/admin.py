from django.contrib import admin, messages

from apps.core.admin_utils import BaseAdmin

from .models import ODD, Inscription, JalonProjet, Programme, Projet, Session


@admin.register(ODD)
class ODDAdmin(BaseAdmin):
    list_display = ("numero", "intitule")
    search_fields = ("intitule",)


class SessionInline(admin.TabularInline):
    model = Session
    extra = 0
    fields = ("titre", "debut", "fin", "espace", "capacite")
    show_change_link = True


@admin.register(Programme)
class ProgrammeAdmin(BaseAdmin):
    list_display = ("titre", "type", "centre", "date_debut", "date_fin", "responsable", "budget")
    list_filter = ("centre", "type", "odd")
    search_fields = ("titre", "description")
    autocomplete_fields = ("responsable",)
    filter_horizontal = ("partenaires", "odd")
    inlines = [SessionInline]
    date_hierarchy = "date_debut"


class InscriptionInline(admin.TabularInline):
    model = Inscription
    extra = 0
    autocomplete_fields = ("usager",)
    fields = ("usager", "statut", "certificat_delivre", "evaluation")


@admin.register(Session)
class SessionAdmin(BaseAdmin):
    list_display = ("titre", "programme", "debut", "fin", "espace", "capacite", "places_restantes")
    list_filter = ("programme__centre", "programme__type", "en_ligne", "espace")
    search_fields = ("titre", "programme__titre")
    autocomplete_fields = ("programme", "espace")
    filter_horizontal = ("formateurs",)
    inlines = [InscriptionInline]
    date_hierarchy = "debut"


@admin.action(description="Marquer présent·e·s")
def marquer_presents(modeladmin, request, queryset):
    n = queryset.exclude(statut=Inscription.Statut.ANNULEE).update(statut=Inscription.Statut.PRESENT)
    messages.success(request, f"{n} présence(s) enregistrée(s).")


@admin.action(description="Délivrer le certificat (présent·e·s uniquement)")
def delivrer_certificat(modeladmin, request, queryset):
    n = queryset.filter(statut=Inscription.Statut.PRESENT).update(certificat_delivre=True)
    messages.success(request, f"{n} certificat(s) délivré(s).")


@admin.register(Inscription)
class InscriptionAdmin(BaseAdmin):
    list_display = ("usager", "session", "statut", "certificat_delivre", "evaluation")
    list_filter = ("statut", "certificat_delivre", "session__programme")
    search_fields = ("usager__nom", "usager__prenom", "session__titre")
    autocomplete_fields = ("usager", "session")
    actions = BaseAdmin.actions + [marquer_presents, delivrer_certificat]


class JalonInline(admin.TabularInline):
    model = JalonProjet
    extra = 0
    fields = ("date", "titre", "stade_atteint", "description")


@admin.register(Projet)
class ProjetAdmin(BaseAdmin):
    list_display = ("titre", "porteur", "domaine", "stade", "statut", "programme", "mentor", "emplois_crees")
    list_filter = ("centre", "stade", "statut", "domaine", "programme", "odd")
    search_fields = ("titre", "description", "porteur__nom", "porteur__prenom")
    autocomplete_fields = ("porteur", "membres", "programme", "mentor")
    filter_horizontal = ("odd",)
    inlines = [JalonInline]
