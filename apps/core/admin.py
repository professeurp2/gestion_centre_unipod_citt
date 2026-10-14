from django.contrib import admin

from .admin_utils import BaseAdmin
from .models import Centre, Espace, Partenaire

admin.site.site_header = "UNIPOD Mali — Gestion du centre"
admin.site.site_title = "UNIPOD Mali"
admin.site.index_title = "Administration de la plateforme"


class EspaceInline(admin.TabularInline):
    model = Espace
    extra = 0
    fields = ("nom", "type", "capacite", "responsable", "actif")


@admin.register(Centre)
class CentreAdmin(BaseAdmin):
    list_display = ("nom", "code", "ville", "pays", "universite_hote", "actif")
    list_filter = ("pays", "actif")
    search_fields = ("nom", "code", "universite_hote")
    inlines = [EspaceInline]


@admin.register(Espace)
class EspaceAdmin(BaseAdmin):
    list_display = ("nom", "centre", "type", "capacite", "responsable", "actif")
    list_filter = ("centre", "type", "actif")
    search_fields = ("nom",)
    autocomplete_fields = ("responsable",)


@admin.register(Partenaire)
class PartenaireAdmin(BaseAdmin):
    list_display = ("nom", "type", "contact", "email", "telephone")
    list_filter = ("type", "centres")
    search_fields = ("nom", "contact")
    filter_horizontal = ("centres",)
