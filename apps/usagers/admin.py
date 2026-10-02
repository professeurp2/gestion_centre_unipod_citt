from django.contrib import admin
from django.utils import timezone

from apps.core.admin_utils import BaseAdmin
from apps.equipements.models import Habilitation

from .models import Usager, Visite


class HabilitationInline(admin.TabularInline):
    model = Habilitation
    extra = 0
    fields = ("categorie", "date_obtention", "date_expiration", "formateur")
    autocomplete_fields = ("formateur",)


@admin.register(Usager)
class UsagerAdmin(BaseAdmin):
    list_display = ("numero_carte", "nom", "prenom", "genre", "categorie", "etablissement", "date_adhesion", "statut")
    list_filter = ("centre", "statut", "categorie", "genre", "situation_handicap")
    search_fields = ("numero_carte", "nom", "prenom", "email", "telephone", "etablissement")
    date_hierarchy = "date_adhesion"
    inlines = [HabilitationInline]


@admin.action(description="Enregistrer le départ maintenant")
def enregistrer_depart(modeladmin, request, queryset):
    queryset.filter(depart__isnull=True).update(depart=timezone.now())


@admin.register(Visite)
class VisiteAdmin(BaseAdmin):
    list_display = ("usager", "motif", "espace", "arrivee", "depart", "duree_heures")
    list_filter = ("motif", "espace", "usager__centre")
    search_fields = ("usager__nom", "usager__prenom", "usager__numero_carte")
    autocomplete_fields = ("usager",)
    date_hierarchy = "arrivee"
    actions = BaseAdmin.actions + [enregistrer_depart]
