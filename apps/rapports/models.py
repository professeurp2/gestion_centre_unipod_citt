"""Cibles annuelles des indicateurs de performance (cadre de résultats UNIPOD)."""
from django.db import models

from apps.core.models import Centre

from .indicateurs import choix_indicateurs


class Cible(models.Model):
    """Valeur cible d'un indicateur pour une année donnée."""

    centre = models.ForeignKey(Centre, on_delete=models.CASCADE, related_name="cibles")
    annee = models.PositiveSmallIntegerField("année")
    indicateur = models.CharField("indicateur", max_length=40, choices=choix_indicateurs)
    valeur = models.DecimalField("valeur cible", max_digits=14, decimal_places=0)

    class Meta:
        verbose_name = "cible d'indicateur"
        verbose_name_plural = "cibles d'indicateurs"
        ordering = ["-annee", "indicateur"]
        constraints = [
            models.UniqueConstraint(fields=["centre", "annee", "indicateur"], name="cible_unique"),
        ]

    def __str__(self):
        return f"{self.indicateur} {self.annee} : {self.valeur}"
