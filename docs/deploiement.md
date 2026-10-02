# Déploiement sans frais

Contrainte : la plateforme doit fonctionner **longtemps sans coût récurrent**.
Elle n'utilise donc que des logiciels libres (Django, Django REST Framework,
django-filter, WhiteNoise, Gunicorn) et **SQLite** : la base est un simple
fichier, sans serveur de base de données à payer ni à administrer. SQLite
convient largement au volume d'un centre (quelques dizaines d'utilisateurs
simultanés, des centaines de milliers d'enregistrements).

> ⚠️ Les offres « gratuites » des hébergeurs changent souvent. Vérifiez les
> conditions en vigueur avant de choisir, et évitez toute offre qui supprime
> la base de données au bout de quelques semaines ou qui exige une carte
> bancaire susceptible d'être débitée.

## Option recommandée : serveur local au centre (0 F/mois)

Un ordinateur existant du centre ou de l'université (même ancien, 2 Go de RAM
suffisent) sous Ubuntu Server (gratuit). Avantages : aucun abonnement, données
hébergées au Mali, fonctionne même quand la connexion internet est coupée.

```bash
sudo apt install -y python3-venv git
sudo mkdir -p /srv/unipod && sudo chown $USER /srv/unipod && cd /srv/unipod
git clone https://github.com/professeurp2/gestion_centre_unipod_citt.git app && cd app
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # puis éditer : SECRET_KEY, ALLOWED_HOSTS (IP du serveur)…
set -a && . ./.env && set +a
python manage.py migrate && python manage.py init_unipod && python manage.py createsuperuser
python manage.py collectstatic --noinput
```

Générer la clé secrète :
`python -c "import secrets; print(secrets.token_urlsafe(50))"`.

Service permanent `/etc/systemd/system/unipod.service` :

```ini
[Unit]
Description=Plateforme UNIPOD
After=network.target

[Service]
User=<utilisateur>
WorkingDirectory=/srv/unipod/app
EnvironmentFile=/srv/unipod/app/.env
ExecStart=/srv/unipod/app/.venv/bin/gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now unipod
```

Le site est alors accessible sur `http://<IP-du-serveur>:8000` depuis le réseau
du centre (les fichiers statiques sont servis par WhiteNoise, sans Nginx).

**Accès depuis internet (facultatif, gratuit)** : demander à la DSI de
l'université d'ouvrir un nom de domaine/port vers ce serveur, ou utiliser un
tunnel gratuit (ex. Cloudflare Tunnel) ; dans ce cas passer `DJANGO_HTTPS=true`
et renseigner `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Option hébergée : PythonAnywhere (offre gratuite)

Hébergement Python avec une offre gratuite durable, adaptée à SQLite (le
disque est persistant). Limites à connaître : adresse en
`<compte>.pythonanywhere.com`, espace disque réduit, accès internet sortant
restreint (envoi d'e-mails/SMS limité), et l'application doit être
**prolongée manuellement** depuis le tableau de bord à intervalle régulier.

Étapes : créer le compte → console Bash → `git clone …` → créer le virtualenv
et `pip install -r requirements.txt` → onglet *Web* : application « Manual
configuration », pointer le fichier WSGI sur `config.wsgi`, définir les
variables d'environnement dans ce fichier WSGI, mapper `/static/` vers
`staticfiles/` → `migrate`, `init_unipod`, `createsuperuser`,
`collectstatic`.

## À éviter

- Les offres où la base PostgreSQL gratuite expire ou est suspendue après
  quelques jours/semaines d'inactivité.
- Les hébergements à disque éphémère (le fichier SQLite y serait perdu à
  chaque redémarrage).

## Sauvegardes (indispensable, gratuit)

```bash
python manage.py sauvegarde            # copie datée dans SAUVEGARDE_DIR, garde les 30 dernières
python manage.py sauvegarde --garder 60
```

La copie est cohérente même pendant l'utilisation. Planifier chaque nuit
(`crontab -e`) :

```
0 2 * * * cd /srv/unipod/app && set -a && . ./.env && set +a && .venv/bin/python manage.py sauvegarde
```

…et copier régulièrement le dossier de sauvegardes hors du serveur (disque
externe, clé USB, espace de stockage de l'université). Restaurer = arrêter le
service, remplacer `db.sqlite3` par une sauvegarde, redémarrer.

## Mises à jour

```bash
cd /srv/unipod/app && git pull && . .venv/bin/activate && set -a && . ./.env && set +a
pip install -r requirements.txt && python manage.py sauvegarde && python manage.py migrate
python manage.py collectstatic --noinput && sudo systemctl restart unipod
```

## Environnement de test sur Railway (payant après la période d'essai)

Railway est pratique pour **tester** la plateforme en ligne, mais ce n'est pas
une solution sans frais durable : après les crédits d'essai, il faut un
abonnement payant (vérifier les conditions en vigueur). À réserver aux tests.

1. Sur railway.com : *New Project* → *Deploy from GitHub repo* →
   `gestion_centre_unipod_citt` (choisir la branche à tester dans les
   paramètres du service si elle n'est pas encore fusionnée).
2. Onglet *Variables* du service :

   | Variable | Valeur |
   |---|---|
   | `DJANGO_SECRET_KEY` | longue valeur aléatoire |
   | `DJANGO_DEBUG` | `false` |
   | `DJANGO_SUPERUSER_USERNAME` | `admin` (ou autre) |
   | `DJANGO_SUPERUSER_PASSWORD` | mot de passe solide |
   | `DEMO` | `true` pour charger les données fictives |
   | `SQLITE_PATH` | `/data/db.sqlite3` (si un volume est monté sur `/data`) |

3. *Settings* → *Networking* → *Generate Domain* : le domaine est pris en
   compte automatiquement (`RAILWAY_PUBLIC_DOMAIN`).
4. Facultatif : *New* → *Volume* monté sur `/data` pour que la base survive
   aux redéploiements ; sans volume, la base est **recréée à chaque
   déploiement** (acceptable pour une démonstration).

Le fichier `railway.json` et le script `scripts/demarrage.sh` s'occupent du
reste (migrations, fichiers statiques, référentiels, compte administrateur,
démarrage de Gunicorn).
