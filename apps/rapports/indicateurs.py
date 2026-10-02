"""Registre des indicateurs clés (KPI) inspirés du cadre de résultats UNIPOD.

Pour ajouter un indicateur, il suffit de décorer une fonction avec
``@indicateur(code, libelle, theme)`` : il apparaît alors automatiquement dans
le tableau de bord, l'API, l'export CSV et la liste des cibles.

Chaque fonction reçoit ``(centre, debut, fin)`` — ``centre`` peut être ``None``
(consolidation tous centres) — et renvoie un nombre ou un dict
``{"valeur": ..., "femmes": ...}`` pour la désagrégation par genre.
"""
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal

from django.db.models import Count, F, Q, Sum
from django.utils import timezone

REGISTRE = {}


@dataclass(frozen=True)
class Indicateur:
    code: str
    libelle: str
    theme: str
    fonction: callable
    unite: str = ""


def indicateur(code, libelle, theme, unite=""):
    def deco(fn):
        REGISTRE[code] = Indicateur(code, libelle, theme, fn, unite)
        return fn

    return deco


def choix_indicateurs():
    return [(i.code, f"{i.theme} — {i.libelle}") for i in REGISTRE.values()]


def _filtre_centre(qs, centre, champ="centre"):
    return qs.filter(**{champ: centre}) if centre else qs


def _dt(d, fin=False):
    return timezone.make_aware(datetime.combine(d, time.max if fin else time.min))


def _avec_genre(qs, champ_genre="genre"):
    total = qs.count()
    femmes = qs.filter(**{champ_genre: "F"}).count()
    return {"valeur": total, "femmes": femmes}


# --- Usagers & fréquentation --------------------------------------------------

@indicateur("usagers_actifs", "Usagers inscrits actifs", "Usagers")
def usagers_actifs(centre, debut, fin):
    from apps.usagers.models import Usager

    qs = _filtre_centre(Usager.objects.filter(statut=Usager.Statut.ACTIF, date_adhesion__lte=fin), centre)
    return _avec_genre(qs)


@indicateur("nouveaux_usagers", "Nouveaux usagers sur la période", "Usagers")
def nouveaux_usagers(centre, debut, fin):
    from apps.usagers.models import Usager

    qs = _filtre_centre(Usager.objects.filter(date_adhesion__range=(debut, fin)), centre)
    return _avec_genre(qs)


@indicateur("visites", "Visites enregistrées", "Usagers")
def visites(centre, debut, fin):
    from apps.usagers.models import Visite

    qs = _filtre_centre(Visite.objects.filter(arrivee__range=(_dt(debut), _dt(fin, True))), centre, "usager__centre")
    return _avec_genre(qs, "usager__genre")


# --- Formation ------------------------------------------------------------------

@indicateur("sessions_tenues", "Sessions de formation / événements tenus", "Formation")
def sessions_tenues(centre, debut, fin):
    from apps.programmes.models import Session

    qs = Session.objects.filter(debut__range=(_dt(debut), _dt(fin, True)))
    return _filtre_centre(qs, centre, "programme__centre").count()


@indicateur("personnes_formees", "Personnes formées (présentes au moins une fois)", "Formation")
def personnes_formees(centre, debut, fin):
    from apps.usagers.models import Usager

    filtre = Q(
        inscriptions__statut="present",
        inscriptions__session__debut__range=(_dt(debut), _dt(fin, True)),
    )
    qs = _filtre_centre(Usager.objects.filter(filtre).distinct(), centre)
    return _avec_genre(qs)


@indicateur("certificats", "Certificats délivrés", "Formation")
def certificats(centre, debut, fin):
    from apps.programmes.models import Inscription

    qs = Inscription.objects.filter(
        certificat_delivre=True, session__debut__range=(_dt(debut), _dt(fin, True))
    )
    return _avec_genre(_filtre_centre(qs, centre, "session__programme__centre"), "usager__genre")


# --- Innovation & entrepreneuriat ----------------------------------------------

@indicateur("projets_actifs", "Projets d'innovation accompagnés (actifs)", "Innovation")
def projets_actifs(centre, debut, fin):
    from apps.programmes.models import Projet

    qs = Projet.objects.filter(statut=Projet.Statut.ACTIF, date_debut__lte=fin)
    return _avec_genre(_filtre_centre(qs, centre), "porteur__genre")


@indicateur("prototypes", "Projets ayant atteint au moins le stade prototype", "Innovation")
def prototypes(centre, debut, fin):
    from apps.programmes.models import Projet

    qs = Projet.objects.exclude(stade=Projet.Stade.IDEATION).filter(date_debut__lte=fin)
    return _filtre_centre(qs, centre).count()


@indicateur("startups", "Startups créées", "Innovation")
def startups(centre, debut, fin):
    from apps.programmes.models import Projet

    qs = Projet.objects.filter(
        stade__in=[Projet.Stade.STARTUP, Projet.Stade.COMMERCIALISATION], date_debut__lte=fin
    )
    return _avec_genre(_filtre_centre(qs, centre), "porteur__genre")


@indicateur("emplois_crees", "Emplois créés par les projets", "Innovation")
def emplois_crees(centre, debut, fin):
    from apps.programmes.models import Projet

    qs = _filtre_centre(Projet.objects.filter(date_debut__lte=fin), centre)
    return qs.aggregate(t=Sum("emplois_crees"))["t"] or 0


@indicateur("fonds_mobilises", "Fonds mobilisés par les projets", "Innovation", "FCFA")
def fonds_mobilises(centre, debut, fin):
    from apps.programmes.models import Projet

    qs = _filtre_centre(Projet.objects.filter(date_debut__lte=fin), centre)
    return qs.aggregate(t=Sum("fonds_mobilises"))["t"] or 0


# --- Équipements ----------------------------------------------------------------

@indicateur("heures_machine", "Heures d'utilisation des machines", "Équipements", "h")
def heures_machine(centre, debut, fin):
    from apps.equipements.models import Reservation

    qs = Reservation.objects.filter(statut="terminee", debut__range=(_dt(debut), _dt(fin, True)))
    qs = _filtre_centre(qs, centre, "equipement__centre")
    total = sum(((r.fin - r.debut).total_seconds() for r in qs.only("debut", "fin")), 0)
    return round(total / 3600, 1)


@indicateur("disponibilite_machines", "Taux de disponibilité du parc", "Équipements", "%")
def disponibilite_machines(centre, debut, fin):
    from apps.equipements.models import Equipement

    qs = _filtre_centre(Equipement.objects.exclude(etat=Equipement.Etat.HORS_SERVICE), centre)
    total = qs.count()
    if not total:
        return 0
    return round(100 * qs.filter(etat=Equipement.Etat.OPERATIONNEL).count() / total, 1)


@indicateur("incidents_ouverts", "Incidents non résolus", "Équipements")
def incidents_ouverts(centre, debut, fin):
    from apps.equipements.models import Incident

    qs = Incident.objects.exclude(statut=Incident.Statut.RESOLU)
    return _filtre_centre(qs, centre, "equipement__centre").count()


@indicateur("cout_maintenance", "Coût des maintenances réalisées", "Équipements", "FCFA")
def cout_maintenance(centre, debut, fin):
    from apps.equipements.models import Maintenance

    qs = Maintenance.objects.filter(statut="terminee", date_realisation__range=(debut, fin))
    return _filtre_centre(qs, centre, "equipement__centre").aggregate(t=Sum("cout"))["t"] or 0


# --- Stocks ---------------------------------------------------------------------

@indicateur("articles_en_alerte", "Articles sous le seuil d'alerte", "Stocks")
def articles_en_alerte(centre, debut, fin):
    from apps.stocks.models import Article

    qs = Article.objects.filter(actif=True, quantite__lte=F("seuil_alerte"))
    return _filtre_centre(qs, centre).count()


@indicateur("valeur_stock", "Valeur du stock", "Stocks", "FCFA")
def valeur_stock(centre, debut, fin):
    from apps.stocks.models import Article

    qs = _filtre_centre(Article.objects.filter(actif=True), centre)
    return sum((a.quantite * a.prix_unitaire for a in qs.only("quantite", "prix_unitaire")), Decimal("0"))


@indicateur("consommation_stock", "Valeur des consommations (sorties)", "Stocks", "FCFA")
def consommation_stock(centre, debut, fin):
    from apps.stocks.models import MouvementStock

    qs = MouvementStock.objects.filter(type="sortie", date__range=(_dt(debut), _dt(fin, True)))
    qs = _filtre_centre(qs, centre, "article__centre").select_related("article")
    return sum((m.quantite * m.article.prix_unitaire for m in qs), Decimal("0"))


# --- Personnel ------------------------------------------------------------------

@indicateur("effectif", "Effectif du personnel actif", "Personnel")
def effectif(centre, debut, fin):
    from apps.personnel.models import Personnel

    qs = Personnel.objects.exclude(statut=Personnel.Statut.SORTI)
    return _avec_genre(_filtre_centre(qs, centre))


@indicateur("jours_conge", "Jours de congé approuvés sur la période", "Personnel", "j")
def jours_conge(centre, debut, fin):
    from apps.personnel.models import Conge

    qs = Conge.objects.filter(statut="approuve", date_debut__lte=fin, date_fin__gte=debut)
    qs = _filtre_centre(qs, centre, "personnel__centre")
    return sum(((min(c.date_fin, fin) - max(c.date_debut, debut)).days + 1 for c in qs), 0)


def calculer(centre=None, debut=None, fin=None, codes=None):
    """Calcule les indicateurs et renvoie une liste de dicts prêts à afficher."""
    from .models import Cible

    fin = fin or timezone.localdate()
    debut = debut or fin.replace(month=1, day=1)
    cibles = {}
    if centre:
        cibles = dict(
            Cible.objects.filter(centre=centre, annee=fin.year).values_list("indicateur", "valeur")
        )
    resultats = []
    for code, ind in REGISTRE.items():
        if codes and code not in codes:
            continue
        brut = ind.fonction(centre, debut, fin)
        valeur, femmes = (brut["valeur"], brut["femmes"]) if isinstance(brut, dict) else (brut, None)
        if isinstance(valeur, Decimal) and valeur == valeur.to_integral_value():
            valeur = int(valeur)
        cible = cibles.get(code)
        resultats.append(
            {
                "code": code,
                "libelle": ind.libelle,
                "theme": ind.theme,
                "unite": ind.unite,
                "valeur": valeur,
                "femmes": femmes,
                "part_femmes": round(100 * femmes / valeur, 1) if femmes is not None and valeur else None,
                "cible": cible,
                "taux_realisation": round(100 * Decimal(valeur) / cible, 1) if cible else None,
            }
        )
    return resultats
