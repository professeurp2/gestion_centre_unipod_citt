import sqlite3
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import call_command
from django.test import TransactionTestCase

from apps.core.models import Centre


class SauvegardeTests(TransactionTestCase):
    def test_sauvegarde_et_rotation(self):
        Centre.objects.create(code="sauv", nom="Centre sauvegardé")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base.sqlite3"
            # La base de test SQLite est en mémoire : on la recopie dans un fichier.
            from django.db import connection

            connection.ensure_connection()
            fichier = sqlite3.connect(base)
            connection.connection.backup(fichier)
            fichier.close()
            dossier = Path(tmp) / "sauvegardes"
            db = {**settings.DATABASES["default"], "NAME": str(base)}
            with mock.patch.dict(settings.DATABASES, {"default": db}):
                for _ in range(3):
                    call_command("sauvegarde", dossier=str(dossier), garder=2, stdout=StringIO())
            copies = sorted(dossier.glob("unipod_*.sqlite3"))
            self.assertEqual(len(copies), 2)
            nom = sqlite3.connect(copies[-1]).execute("select nom from core_centre where code='sauv'").fetchone()
            self.assertEqual(nom, ("Centre sauvegardé",))
