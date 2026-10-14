"""Sauvegarde à chaud de la base SQLite, avec rotation des anciennes copies.

À planifier chaque jour (cron, tâche planifiée Windows ou « Scheduled task »
PythonAnywhere), puis copier le dossier de sauvegarde sur un support externe
(clé USB, disque, Google Drive de l'université…).
"""
import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = "Crée une copie datée de la base SQLite et conserve les N plus récentes."

    def add_arguments(self, parser):
        parser.add_argument("--dossier", help="Dossier de destination (défaut : SAUVEGARDE_DIR).")
        parser.add_argument("--garder", type=int, default=30, help="Nombre de sauvegardes conservées (défaut 30).")

    def handle(self, *args, **o):
        if connection.vendor != "sqlite":
            raise CommandError("Cette commande concerne SQLite ; pour PostgreSQL, utilisez pg_dump.")
        dossier = Path(o["dossier"] or settings.SAUVEGARDE_DIR)
        dossier.mkdir(parents=True, exist_ok=True)
        cible = dossier / f"unipod_{timezone.localtime():%Y%m%d_%H%M%S_%f}.sqlite3"

        source = sqlite3.connect(settings.DATABASES["default"]["NAME"])
        destination = sqlite3.connect(cible)
        try:
            source.backup(destination)  # copie cohérente même pendant l'utilisation
        finally:
            destination.close()
            source.close()

        anciennes = sorted(dossier.glob("unipod_*.sqlite3"), reverse=True)[max(o["garder"], 1):]
        for f in anciennes:
            f.unlink()
        self.stdout.write(self.style.SUCCESS(f"Sauvegarde créée : {cible} ({len(anciennes)} ancienne(s) supprimée(s))."))
