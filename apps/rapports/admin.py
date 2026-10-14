from django.contrib import admin

from apps.core.admin_utils import BaseAdmin

from .models import Cible


@admin.register(Cible)
class CibleAdmin(BaseAdmin):
    list_display = ("indicateur", "annee", "centre", "valeur")
    list_filter = ("annee", "centre", "indicateur")
