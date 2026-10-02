"""Charge un jeu de données fictif pour découvrir la plateforme (ne pas utiliser en production)."""
import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.models import Centre, Espace, Partenaire
from apps.equipements.models import CategorieEquipement, Equipement, Habilitation, Incident, Maintenance, Reservation
from apps.personnel.models import Conge, Departement, Personnel, Poste
from apps.programmes.models import ODD, Inscription, Programme, Projet, Session
from apps.rapports.models import Cible
from apps.stocks.models import Article, CategorieArticle, Commande, Fournisseur, LigneCommande, MouvementStock
from apps.usagers.models import Usager, Visite

PRENOMS_F = ["Aminata", "Fatoumata", "Mariam", "Awa", "Kadiatou", "Oumou", "Djeneba", "Aïssata"]
PRENOMS_H = ["Moussa", "Ibrahim", "Seydou", "Bakary", "Mamadou", "Souleymane", "Adama", "Boubacar"]
NOMS = ["Traoré", "Coulibaly", "Diarra", "Keïta", "Konaté", "Sangaré", "Touré", "Dembélé", "Maïga", "Cissé"]


class Command(BaseCommand):
    help = "Charge des données de démonstration dans le centre UNIPOD Mali."

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        call_command("init_unipod", stdout=self.stdout)
        centre = Centre.objects.get(code="unipod-mali")
        if centre.usagers.exists():
            self.stdout.write(self.style.WARNING("Des données existent déjà : rien n'a été ajouté."))
            return
        maintenant = timezone.now()
        aujourdhui = timezone.localdate()
        espaces = {e.type: e for e in centre.espaces.all()}

        Partenaire.objects.get_or_create(nom="PNUD Mali", defaults={"type": "bailleur"})[0].centres.add(centre)

        # Personnel
        postes = {p.intitule: p for p in Poste.objects.all()}
        deps = {d.nom: d for d in Departement.objects.filter(centre=centre)}
        equipe = [
            ("Coordinateur·rice du centre", "Direction / coordination", "F", "cdi", None),
            ("Fab manager", "Opérations techniques (Makerspace)", "H", "cdi", None),
            ("Ingénieur·e électronique / IoT", "Opérations techniques (Makerspace)", "F", "cdd", 45),
            ("Chargé·e de programmes", "Programmes & innovation", "H", "cdd", 300),
            ("Gestionnaire de stock / logistique", "Administration & finances", "H", "cdi", None),
            ("Agent d'accueil", "Administration & finances", "F", "volontaire", 120),
        ]
        personnel = []
        for i, (poste, dep, genre, contrat, fin_jours) in enumerate(equipe, 1):
            prenom = random.choice(PRENOMS_F if genre == "F" else PRENOMS_H)
            personnel.append(Personnel.objects.create(
                centre=centre, matricule=f"UPM-{i:03d}", nom=random.choice(NOMS), prenom=prenom, genre=genre,
                poste=postes[poste], departement=deps[dep], type_contrat=contrat,
                date_debut=aujourdhui - timedelta(days=400),
                date_fin=aujourdhui + timedelta(days=fin_jours) if fin_jours else None, solde_conges=22,
            ))
        fab_manager = personnel[1]
        Conge.objects.create(personnel=personnel[3], date_debut=aujourdhui + timedelta(days=10),
                             date_fin=aujourdhui + timedelta(days=14), motif="Congé annuel")

        # Usagers
        categories = ["etudiant"] * 6 + ["enseignant", "entrepreneur", "alumni", "artisan"]
        usagers = []
        for i in range(1, 61):
            genre = "F" if i % 5 in (0, 1) else "H"
            usagers.append(Usager.objects.create(
                centre=centre, numero_carte=f"M-{aujourdhui.year}-{i:04d}", genre=genre,
                prenom=random.choice(PRENOMS_F if genre == "F" else PRENOMS_H), nom=random.choice(NOMS),
                categorie=random.choice(categories), etablissement=random.choice(["USTTB", "ENI-ABT", "ULSHB", "USSGB"]),
                date_adhesion=aujourdhui - timedelta(days=random.randint(0, 250)), consentement_donnees=True,
            ))
        for _ in range(150):
            arrivee = maintenant - timedelta(days=random.randint(0, 200), hours=random.randint(0, 6))
            Visite.objects.create(usager=random.choice(usagers), motif=random.choice(Visite.Motif.values),
                                  espace=random.choice(list(espaces.values())), arrivee=arrivee,
                                  depart=arrivee + timedelta(hours=random.randint(1, 5)))

        # Fournisseurs & stocks
        fournisseur = Fournisseur.objects.create(nom="Bamako Tech Distribution", telephone="+223 20 00 00 00")
        cat_art = {c.nom: c for c in CategorieArticle.objects.all()}
        articles = [
            Article.objects.create(centre=centre, reference=ref, designation=des, categorie=cat_art[cat], unite=u,
                                   seuil_alerte=seuil, prix_unitaire=prix, emplacement=espaces["stockage"],
                                   fournisseur_habituel=fournisseur)
            for ref, des, cat, u, seuil, prix in [
                ("FIL-PLA-1K", "Filament PLA 1,75 mm (1 kg)", "Filament 3D", "bobine", 5, 15000),
                ("MDF-3MM", "Panneau MDF 3 mm 60×40", "Panneaux (MDF, contreplaqué, acrylique)", "plaque", 20, 2500),
                ("ACR-3MM", "Plaque acrylique 3 mm", "Panneaux (MDF, contreplaqué, acrylique)", "plaque", 10, 6000),
                ("ESP32", "Carte ESP32 DevKit", "Cartes microcontrôleurs & capteurs", "piece", 10, 5000),
                ("ETAIN", "Fil d'étain 0,8 mm", "Consommables de soudure", "rouleau", 3, 7500),
                ("GANTS", "Gants de protection", "EPI (lunettes, gants, masques)", "boite", 2, 4000),
            ]
        ]
        for a, q in zip(articles, [30, 50, 8, 40, 6, 1]):
            MouvementStock.objects.create(article=a, type="entree", quantite=q, motif="Stock initial")
        commande = Commande.objects.create(centre=centre, numero=f"BC-{aujourdhui.year}-001", fournisseur=fournisseur,
                                           statut="envoyee", ligne_budgetaire="PNUD — Fonds UNIPOD")
        LigneCommande.objects.create(commande=commande, article=articles[2], quantite=20, prix_unitaire=6000)

        # Équipements
        cat_eq = {c.nom: c for c in CategorieEquipement.objects.all()}
        parc = [
            ("Imprimante 3D Prusa MK4", "Imprimante 3D FDM", "makerspace", "faible", True, 90),
            ("Imprimante 3D Prusa MK4 (2)", "Imprimante 3D FDM", "makerspace", "faible", True, 90),
            ("Découpeuse laser 100 W", "Découpeuse laser CO2", "makerspace", "eleve", True, 60),
            ("Fraiseuse CNC 1,2×2,4 m", "Fraiseuse CNC grand format", "makerspace", "eleve", True, 60),
            ("Station de soudure Weller", "Station de soudure", "electronique", "moyen", True, 180),
            ("Oscilloscope 4 voies", "Oscilloscope / générateur", "electronique", "faible", False, 365),
            ("Station IA (GPU)", "Poste de travail CAO / IA", "numerique", "faible", False, 180),
        ]
        equipements = []
        for i, (nom, cat, esp, risque, hab, perio) in enumerate(parc, 1):
            equipements.append(Equipement.objects.create(
                centre=centre, code_inventaire=f"UPM-EQ-{i:03d}", nom=nom, categorie=cat_eq[cat], espace=espaces[esp],
                niveau_risque=risque, habilitation_requise=hab, periodicite_maintenance=perio,
                date_acquisition=aujourdhui - timedelta(days=perio + random.randint(-10, 30)),
                source_financement="PNUD", fournisseur=fournisseur, responsable=fab_manager,
            ))
        Incident.objects.create(equipement=equipements[3], gravite="majeure", description="Broche bloquée")
        Maintenance.objects.create(equipement=equipements[0], type="preventive", statut="terminee",
                                   date_planifiee=aujourdhui - timedelta(days=30),
                                   date_realisation=aujourdhui - timedelta(days=30),
                                   intervenant=fab_manager, description="Nettoyage buse, calibration plateau")
        for u in usagers[:25]:
            for cat in ("Imprimante 3D FDM", "Découpeuse laser CO2"):
                Habilitation.objects.create(usager=u, categorie=cat_eq[cat], formateur=fab_manager,
                                            date_obtention=aujourdhui - timedelta(days=200))
        for j in range(40):
            debut = (maintenant - timedelta(days=j * 4)).replace(hour=9 + j % 6, minute=0, second=0, microsecond=0)
            r = Reservation(equipement=equipements[j % 3], usager=usagers[j % 25], debut=debut,
                            fin=debut + timedelta(hours=2), statut="terminee" if j else "confirmee",
                            objet="Prototype")
            r.full_clean()
            r.save()
        for _ in range(12):
            MouvementStock.objects.create(article=articles[0], type="sortie", quantite=1,
                                          usager=random.choice(usagers[:25]), motif="Impression prototype")

        # Programmes & projets
        odd = {o.numero: o for o in ODD.objects.all()}
        prog = Programme.objects.create(centre=centre, titre="Bootcamp Fabrication numérique", type="bootcamp",
                                        date_debut=aujourdhui - timedelta(days=120), responsable=personnel[3])
        prog.odd.add(odd[4], odd[9])
        incub = Programme.objects.create(centre=centre, titre="Programme d'incubation — cohorte 1", type="incubation",
                                         date_debut=aujourdhui - timedelta(days=200), responsable=personnel[3])
        for k in range(4):
            debut = maintenant - timedelta(days=110 - k * 7)
            s = Session.objects.create(programme=prog, titre=f"Module {k + 1}", debut=debut,
                                       fin=debut + timedelta(hours=4), espace=espaces["formation"], capacite=25)
            s.formateurs.add(fab_manager)
            for u in usagers[k * 10: k * 10 + 20]:
                Inscription.objects.create(session=s, usager=u, statut=random.choice(["present"] * 4 + ["absent"]),
                                           evaluation=random.randint(3, 5))
        for titre, stade, dom, o in [
            ("Séchoir solaire pour mangues", "prototype", "agritech", 2),
            ("Capteur connecté qualité de l'eau", "mvp", "eau", 6),
            ("Prothèse de main imprimée en 3D", "pilote", "sante", 3),
            ("Plateforme e-learning en bambara", "startup", "education", 4),
            ("Foyer amélioré à faible émission", "ideation", "energie", 7),
        ]:
            p = Projet.objects.create(centre=centre, titre=titre, porteur=random.choice(usagers), stade=stade,
                                      domaine=dom, programme=incub, mentor=personnel[3],
                                      emplois_crees=3 if stade == "startup" else 0)
            p.odd.add(odd[o])

        for code, valeur in [("nouveaux_usagers", 500), ("personnes_formees", 300), ("prototypes", 20),
                             ("startups", 5), ("heures_machine", 2000)]:
            Cible.objects.create(centre=centre, annee=aujourdhui.year, indicateur=code, valeur=valeur)

        self.stdout.write(self.style.SUCCESS("Données de démonstration chargées."))
