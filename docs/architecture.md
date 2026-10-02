# Architecture et évolutivité

## Pile technique

- **Django 5.2 LTS** (Python ≥ 3.10) : ORM, authentification, interface de gestion.
- **Django REST Framework** + **django-filter** : API REST pour applications
  mobiles, bornes d'accueil, outils BI ou intégration avec d'autres UNIPOD.
- **SQLite** en développement, **PostgreSQL** en production.

## Organisation

```
config/                 paramètres, URL racines
apps/
  core/                 Centre, Espace, Partenaire, classes de base, API générique,
                        référentiels standards UNIPOD, commandes init_unipod / donnees_demo
  comptes/              Utilisateur (rôle, centre)
  personnel/            RH
  usagers/              bénéficiaires, visites
  equipements/          machines, habilitations, réservations, maintenance, incidents
  stocks/               articles, mouvements, fournisseurs, commandes
  programmes/           programmes, sessions, inscriptions, projets, jalons, ODD
  rapports/             indicateurs (registre), cibles, tableau de bord, exports
templates/              gabarits du tableau de bord
tests/                  tests automatisés
```

## Principes d'évolutivité

1. **Multi-centres** : les entités opérationnelles portent une clé `centre`.
   Ajouter un pod (ex. antenne régionale) = `manage.py init_unipod --code
   unipod-segou --nom "UNIPOD Ségou" --ville Ségou`. Le tableau de bord filtre
   par centre ou consolide.
2. **Référentiels standards paramétrables** : espaces, postes, familles de
   machines, catégories d'articles et ODD sont des données, pas du code.
3. **Indicateurs enregistrables** : un nouvel indicateur est une fonction
   décorée dans `apps/rapports/indicateurs.py` ; il apparaît automatiquement au
   tableau de bord, dans l'API, l'export CSV et la liste des cibles.

   ```python
   @indicateur("brevets", "Brevets déposés", "Innovation")
   def brevets(centre, debut, fin):
       from apps.programmes.models import Projet
       qs = Projet.objects.exclude(propriete_intellectuelle="")
       return (qs.filter(centre=centre) if centre else qs).count()
   ```
4. **API déclarative** : une ligne dans `apps/core/api_ressources.py` expose un
   modèle en CRUD (filtres, recherche, pagination, permissions par modèle et
   validation métier `clean()` appliquée).
5. **Traçabilité** : `Horodatage` / `Tracabilite` (dates, auteur) sur les
   modèles ; mouvements de stock immuables.

## Ajouter un module

1. `django-admin startapp <nom> apps/<nom>` puis renommer `name = "apps.<nom>"`.
2. Ajouter `"apps.<nom>"` à `INSTALLED_APPS`.
3. Créer les modèles (hériter de `Horodatage`, ajouter `centre`), l'admin
   (hériter de `BaseAdmin` pour l'export CSV), les ressources API et, si besoin,
   des indicateurs.
4. Donner les droits aux rôles dans `ROLES` (`apps/core/referentiels.py`) puis
   relancer `init_unipod`.

## Pistes d'évolution

- Portail usagers (auto-inscription, réservation en ligne, QR code de carte).
- Facturation des prestations machines (le tarif horaire est déjà stocké).
- Notifications e-mail/SMS (alertes stock, maintenance, fin de contrat).
- Import/export Excel en masse, tableaux de bord graphiques.
- Authentification unique avec l'université hôte.
