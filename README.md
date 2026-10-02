# Gestion centralisée — UNIPOD Mali

Plateforme web de gestion centralisée du centre **UNIPOD Mali** (University
Innovation Pod, initiative PNUD / *timbuktoo*). Elle couvre l'ensemble des
volets d'un UNIPOD : personnel, usagers, machines du makerspace, stocks,
programmes de formation et d'incubation, et indicateurs de résultats.

Conçue **multi-centres** et **modulaire**, elle peut accueillir d'autres pods ou
antennes et de nouveaux modules sans refonte.

## Modules

| Module | Contenu |
|---|---|
| **Centre & espaces** (`apps/core`) | Centres UNIPOD, espaces standards (Makerspace, labo électronique/IoT, labo numérique/IA, studio design, formation, coworking, incubation…), partenaires |
| **Comptes & accès** (`apps/comptes`) | Utilisateurs, rôle principal synchronisé avec un groupe de permissions |
| **Ressources humaines** (`apps/personnel`) | Départements, postes types UNIPOD, fiches agents, contrats, compétences, congés (circuit de validation + solde), présences |
| **Usagers** (`apps/usagers`) | Bénéficiaires (étudiants, chercheurs, entrepreneurs…), carte membre, désagrégation genre/handicap, registre des visites |
| **Équipements** (`apps/equipements`) | Inventaire machines, habilitations des usagers, réservations (anti-chevauchement, contrôle d'habilitation et d'état), maintenance préventive/corrective, incidents |
| **Stocks** (`apps/stocks`) | Articles/consommables, seuils d'alerte, mouvements tracés et immuables, fournisseurs, bons de commande et réception |
| **Programmes** (`apps/programmes`) | Programmes (formation, bootcamp, hackathon, incubation, accélération…), sessions, inscriptions/présences/certificats, projets d'innovation avec stades de maturité, jalons et ODD |
| **Rapports** (`apps/rapports`) | Tableau de bord, alertes opérationnelles, 20 indicateurs clés (désagrégés par genre), cibles annuelles, export CSV, API |

## Démarrage rapide

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py init_unipod          # centre UNIPOD Mali + référentiels + rôles
python manage.py donnees_demo         # (optionnel) données fictives de démonstration
python manage.py createsuperuser
python manage.py runserver
```

- Tableau de bord : http://127.0.0.1:8000/tableau-de-bord/
- Interface de gestion : http://127.0.0.1:8000/admin/
- API REST : http://127.0.0.1:8000/api/ — indicateurs : `/api/indicateurs/?centre=unipod-mali&debut=2026-01-01&fin=2026-12-31`

Tests : `python manage.py test tests`

## Rôles

`init_unipod` crée les groupes : *Direction*, *Ressources humaines*,
*Technique*, *Magasin*, *Programmes*, *Accueil*, *Lecture seule*. Choisir le
**rôle principal** d'un utilisateur l'affecte automatiquement au groupe
correspondant ; le rôle *Administrateur plateforme* correspond à un
super-utilisateur. Les droits se règlent dans `apps/core/referentiels.py`.

## Règles métier principales

- Le stock n'est jamais saisi à la main : il découle des mouvements (entrée,
  sortie, ajustement, perte). Un mouvement est immuable et un stock ne peut pas
  devenir négatif. La réception d'une commande génère les entrées.
- Une réservation est refusée si le créneau chevauche une autre réservation, si
  la machine n'est pas opérationnelle, ou si l'usager n'a pas l'habilitation
  valide exigée.
- Un incident majeur ou de sécurité met automatiquement la machine « en panne ».
- La date de prochaine maintenance préventive est calculée à partir de la
  périodicité de la machine ; les échéances proches remontent en alerte.
- L'approbation d'un congé annuel le décompte du solde de l'agent.

## Production

Copier `.env.example` en `.env` (ou définir les variables), renseigner
PostgreSQL, puis `python manage.py collectstatic` et servir avec gunicorn
derrière un proxy HTTPS.

Voir [`docs/architecture.md`](docs/architecture.md) pour l'architecture et la
façon d'étendre la plateforme.
