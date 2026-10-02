import csv
from datetime import date, timedelta
from itertools import groupby

from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.models import Centre

from . import indicateurs


def _parametres(request):
    """Lit centre / période depuis la requête (année civile en cours par défaut)."""
    aujourdhui = timezone.localdate()

    def lire_date(nom, defaut):
        try:
            return date.fromisoformat(request.GET.get(nom, ""))
        except ValueError:
            return defaut

    fin = lire_date("fin", aujourdhui)
    debut = lire_date("debut", fin.replace(month=1, day=1))
    centre = None
    code = request.GET.get("centre")
    if code:
        centre = Centre.objects.filter(code=code).first()
    elif getattr(request.user, "centre_id", None):
        centre = request.user.centre
    return centre, debut, fin


def _alertes(centre):
    from apps.equipements.models import Equipement, Incident, Reservation
    from apps.personnel.models import Conge, Personnel
    from apps.stocks.models import Article

    aujourdhui = timezone.localdate()

    def f(qs, champ):
        return qs.filter(**{champ: centre}) if centre else qs

    maintenances_dues = [
        e for e in f(Equipement.objects.exclude(etat=Equipement.Etat.HORS_SERVICE), "centre")
        .filter(periodicite_maintenance__isnull=False)
        if e.prochaine_maintenance and e.prochaine_maintenance <= aujourdhui + timedelta(days=7)
    ]
    return {
        "stock_bas": f(Article.objects.filter(actif=True, quantite__lte=F("seuil_alerte")), "centre")
        .select_related("categorie")[:20],
        "maintenances_dues": maintenances_dues[:20],
        "incidents": f(Incident.objects.exclude(statut=Incident.Statut.RESOLU), "equipement__centre")
        .select_related("equipement")[:20],
        "machines_indisponibles": f(
            Equipement.objects.filter(etat__in=[Equipement.Etat.PANNE, Equipement.Etat.MAINTENANCE]), "centre"
        )[:20],
        "contrats_echeance": f(
            Personnel.objects.exclude(statut=Personnel.Statut.SORTI).filter(
                date_fin__range=(aujourdhui, aujourdhui + timedelta(days=60))
            ),
            "centre",
        ),
        "conges_a_valider": f(Conge.objects.filter(statut=Conge.Statut.DEMANDE), "personnel__centre")
        .select_related("personnel"),
        "reservations_jour": f(
            Reservation.objects.filter(debut__date=aujourdhui, statut__in=Reservation.STATUTS_ACTIFS),
            "equipement__centre",
        ).select_related("equipement", "usager"),
    }


@login_required
def tableau_de_bord(request):
    centre, debut, fin = _parametres(request)
    resultats = indicateurs.calculer(centre, debut, fin)
    themes = [(t, list(items)) for t, items in groupby(resultats, key=lambda r: r["theme"])]
    return render(
        request,
        "rapports/tableau_de_bord.html",
        {
            "centre": centre,
            "centres": Centre.objects.filter(actif=True),
            "debut": debut,
            "fin": fin,
            "themes": themes,
            "alertes": _alertes(centre),
        },
    )


@login_required
def export_indicateurs_csv(request):
    centre, debut, fin = _parametres(request)
    reponse = HttpResponse(content_type="text/csv; charset=utf-8")
    reponse["Content-Disposition"] = f'attachment; filename="indicateurs_{debut}_{fin}.csv"'
    reponse.write("﻿")
    w = csv.writer(reponse, delimiter=";")
    w.writerow([f"Centre : {centre or 'Tous'}", f"Période : {debut} → {fin}"])
    w.writerow(["Thème", "Code", "Indicateur", "Valeur", "Unité", "dont femmes", "% femmes", "Cible", "% réalisation"])
    for r in indicateurs.calculer(centre, debut, fin):
        w.writerow([
            r["theme"], r["code"], r["libelle"], r["valeur"], r["unite"],
            r["femmes"] if r["femmes"] is not None else "",
            r["part_femmes"] if r["part_femmes"] is not None else "",
            r["cible"] if r["cible"] is not None else "",
            r["taux_realisation"] if r["taux_realisation"] is not None else "",
        ])
    return reponse


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_indicateurs(request):
    centre, debut, fin = _parametres(request)
    return Response(
        {
            "centre": centre.code if centre else None,
            "debut": debut,
            "fin": fin,
            "indicateurs": indicateurs.calculer(centre, debut, fin),
        }
    )
