"""Déclaration de toutes les ressources exposées par l'API REST."""
from apps.core.api import ressource
from apps.core.models import Centre, Espace, Partenaire
from apps.equipements.models import CategorieEquipement, Equipement, Habilitation, Incident, Maintenance, Reservation
from apps.personnel.models import Competence, Conge, Departement, Personnel, Poste, Presence
from apps.programmes.models import ODD, Inscription, JalonProjet, Programme, Projet, Session
from apps.rapports.models import Cible
from apps.stocks.models import Article, CategorieArticle, Commande, Fournisseur, LigneCommande, MouvementStock
from apps.usagers.models import Usager, Visite

# Centre
ressource("centres", Centre, recherche=["nom", "code"], filtres=["pays", "actif"])
ressource("espaces", Espace, recherche=["nom"], filtres=["centre", "type", "actif"])
ressource("partenaires", Partenaire, recherche=["nom"], filtres=["type"])

# Personnel
ressource("departements", Departement, recherche=["nom"], filtres=["centre"])
ressource("postes", Poste, recherche=["intitule"])
ressource("competences", Competence, recherche=["nom"])
ressource("personnel", Personnel, recherche=["nom", "prenom", "matricule"],
          filtres=["centre", "statut", "type_contrat", "genre", "departement", "poste"])
ressource("conges", Conge, filtres=["personnel", "statut", "type"])
ressource("presences", Presence, filtres=["personnel", "date"])

# Usagers
ressource("usagers", Usager, recherche=["nom", "prenom", "numero_carte", "etablissement"],
          filtres=["centre", "categorie", "genre", "statut"])
ressource("visites", Visite, filtres=["usager", "espace", "motif"])

# Équipements
ressource("categories-equipement", CategorieEquipement, recherche=["nom"], filtres=["famille"])
ressource("equipements", Equipement, recherche=["nom", "code_inventaire", "numero_serie"],
          filtres=["centre", "espace", "categorie", "etat", "reservable"])
ressource("habilitations", Habilitation, filtres=["usager", "categorie"])
ressource("reservations", Reservation, filtres=["equipement", "usager", "statut", "projet"])
ressource("maintenances", Maintenance, filtres=["equipement", "type", "statut"])
ressource("incidents", Incident, filtres=["equipement", "gravite", "statut"])

# Stocks
ressource("fournisseurs", Fournisseur, recherche=["nom"], filtres=["actif"])
ressource("categories-article", CategorieArticle, recherche=["nom"])
ressource("articles", Article, recherche=["reference", "designation"], filtres=["centre", "categorie", "actif"])
ressource("mouvements-stock", MouvementStock, filtres=["article", "type", "usager", "projet"], ecriture_unique=True)
ressource("commandes", Commande, recherche=["numero"], filtres=["centre", "fournisseur", "statut"])
ressource("lignes-commande", LigneCommande, filtres=["commande", "article"])

# Programmes
ressource("odd", ODD, lecture_seule=True)
ressource("programmes", Programme, recherche=["titre"], filtres=["centre", "type"])
ressource("sessions", Session, recherche=["titre"], filtres=["programme", "espace"])
ressource("inscriptions", Inscription, filtres=["session", "usager", "statut"])
ressource("projets", Projet, recherche=["titre"], filtres=["centre", "stade", "statut", "domaine", "programme"])
ressource("jalons", JalonProjet, filtres=["projet"])

# Rapports
ressource("cibles", Cible, filtres=["centre", "annee", "indicateur"])
