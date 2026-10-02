"""Outils partagés par les interfaces d'administration des modules."""
import csv

from django.contrib import admin
from django.http import HttpResponse


@admin.action(description="Exporter la sélection en CSV")
def exporter_csv(modeladmin, request, queryset):
    meta = queryset.model._meta
    champs = [f for f in meta.fields]
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="{meta.model_name}.csv"'
    reponse.write("﻿")  # BOM pour l'ouverture correcte dans Excel
    writer = csv.writer(reponse, delimiter=";")
    writer.writerow([str(f.verbose_name) for f in champs])
    for obj in queryset:
        ligne = []
        for f in champs:
            if f.choices:
                ligne.append(getattr(obj, f"get_{f.name}_display")())
            else:
                v = getattr(obj, f.name)
                ligne.append("" if v is None else str(v))
        writer.writerow(ligne)
    return reponse


class BaseAdmin(admin.ModelAdmin):
    """Admin de base : export CSV, auteur renseigné automatiquement."""

    actions = [exporter_csv]
    list_per_page = 50

    def save_model(self, request, obj, form, change):
        if not change and hasattr(obj, "cree_par_id") and obj.cree_par_id is None:
            obj.cree_par = request.user
        super().save_model(request, obj, form, change)
