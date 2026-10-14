"""Référentiels standards UNIPOD chargés par ``manage.py init_unipod``.

Ces listes décrivent l'organisation type d'un University Innovation Pod
(PNUD / timbuktoo) ; elles peuvent être complétées librement dans l'interface.
"""

ESPACES = [
    ("Makerspace / Fab Lab", "makerspace", 30),
    ("Laboratoire électronique & IoT", "electronique", 20),
    ("Laboratoire numérique & IA", "numerique", 25),
    ("Studio design", "design", 12),
    ("Salle de formation", "formation", 40),
    ("Espace coworking & idéation", "coworking", 40),
    ("Espace incubation", "incubation", 20),
    ("Salle de réunion", "reunion", 12),
    ("Magasin", "stockage", 0),
]

DEPARTEMENTS = [
    "Direction / coordination",
    "Opérations techniques (Makerspace)",
    "Programmes & innovation",
    "Partenariats & communication",
    "Administration & finances",
]

POSTES = [
    "Coordinateur·rice du centre",
    "Fab manager",
    "Ingénieur·e makerspace",
    "Technicien·ne de laboratoire",
    "Ingénieur·e électronique / IoT",
    "Spécialiste numérique / IA",
    "Designer produit",
    "Chargé·e de programmes",
    "Chargé·e d'incubation",
    "Chargé·e de suivi-évaluation",
    "Chargé·e de communication",
    "Assistant·e administratif·ve et financier·ère",
    "Gestionnaire de stock / logistique",
    "Agent d'accueil",
]

CATEGORIES_EQUIPEMENT = [
    ("Imprimante 3D FDM", "additive"),
    ("Imprimante 3D résine (SLA)", "additive"),
    ("Découpeuse laser CO2", "decoupe"),
    ("Découpeuse vinyle", "decoupe"),
    ("Fraiseuse CNC grand format", "usinage"),
    ("Fraiseuse CNC de précision (PCB)", "usinage"),
    ("Tour / fraiseuse conventionnelle", "usinage"),
    ("Station de soudure", "electronique"),
    ("Kits microcontrôleurs (Arduino, ESP32, Raspberry Pi)", "electronique"),
    ("Oscilloscope / générateur", "mesure"),
    ("Multimètre / alimentation de labo", "mesure"),
    ("Poste de travail CAO / IA", "informatique"),
    ("Serveur / GPU", "informatique"),
    ("Scanner 3D", "informatique"),
    ("Brodeuse / machine à coudre numérique", "textile"),
    ("Outillage électroportatif", "outillage"),
    ("Outillage à main", "outillage"),
    ("Matériel audiovisuel", "audiovisuel"),
    ("Équipement de protection individuelle", "securite"),
]

CATEGORIES_ARTICLE = [
    "Filament 3D",
    "Résine 3D",
    "Panneaux (MDF, contreplaqué, acrylique)",
    "Composants électroniques",
    "Cartes microcontrôleurs & capteurs",
    "Fraises & outils de coupe",
    "Pièces détachées machines",
    "Consommables de soudure",
    "EPI (lunettes, gants, masques)",
    "Fournitures de bureau",
]

ODD = [
    (1, "Pas de pauvreté"),
    (2, "Faim « zéro »"),
    (3, "Bonne santé et bien-être"),
    (4, "Éducation de qualité"),
    (5, "Égalité entre les sexes"),
    (6, "Eau propre et assainissement"),
    (7, "Énergie propre et d'un coût abordable"),
    (8, "Travail décent et croissance économique"),
    (9, "Industrie, innovation et infrastructure"),
    (10, "Inégalités réduites"),
    (11, "Villes et communautés durables"),
    (12, "Consommation et production responsables"),
    (13, "Mesures relatives à la lutte contre les changements climatiques"),
    (14, "Vie aquatique"),
    (15, "Vie terrestre"),
    (16, "Paix, justice et institutions efficaces"),
    (17, "Partenariats pour la réalisation des objectifs"),
]

# Rôle -> {app_label: actions} ; "*" = tous les modèles de l'application.
# Actions : view, add, change, delete.
TOUT = ("view", "add", "change", "delete")
LECTURE = ("view",)
ROLES = {
    "Direction": {app: LECTURE for app in ("core", "personnel", "usagers", "equipements", "stocks", "programmes")}
    | {"rapports": TOUT, "comptes": LECTURE},
    "Ressources humaines": {"personnel": TOUT, "core": LECTURE},
    "Technique": {"equipements": TOUT, "usagers": LECTURE, "stocks": ("view", "add"), "core": LECTURE,
                  "personnel": LECTURE, "programmes": LECTURE},
    "Magasin": {"stocks": TOUT, "equipements": LECTURE, "usagers": LECTURE, "programmes": LECTURE, "core": LECTURE},
    "Programmes": {"programmes": TOUT, "usagers": TOUT, "equipements": LECTURE, "core": LECTURE,
                   "personnel": LECTURE, "rapports": LECTURE},
    "Accueil": {"usagers": TOUT, "equipements": ("view", "add", "change"), "programmes": ("view", "change"),
                "core": LECTURE},
    "Lecture seule": {app: LECTURE for app in
                      ("core", "personnel", "usagers", "equipements", "stocks", "programmes", "rapports")},
}
