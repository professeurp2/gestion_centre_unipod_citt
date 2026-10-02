from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.rapports import indicateurs
from apps.rapports.models import Cible
from apps.stocks.models import Article

from . import fabriques as F


class IndicateursTests(TestCase):
    def test_desagregation_genre_et_cible(self):
        centre = F.centre()
        autre = F.centre("autre")
        F.usager(centre, genre="F")
        F.usager(centre, genre="H")
        F.usager(centre, genre="F")
        F.usager(autre, genre="H")
        annee = timezone.localdate().year
        Cible.objects.create(centre=centre, annee=annee, indicateur="nouveaux_usagers", valeur=6)
        res = {r["code"]: r for r in indicateurs.calculer(centre, date(annee, 1, 1), timezone.localdate())}
        r = res["nouveaux_usagers"]
        self.assertEqual((r["valeur"], r["femmes"], r["part_femmes"]), (3, 2, 66.7))
        self.assertEqual(r["taux_realisation"], 50)
        consolide = {r["code"]: r for r in indicateurs.calculer(None)}
        self.assertEqual(consolide["nouveaux_usagers"]["valeur"], 4)

    def test_tous_les_indicateurs_se_calculent_sur_base_vide(self):
        self.assertEqual(len(indicateurs.calculer()), len(indicateurs.REGISTRE))


@override_settings(ALLOWED_HOSTS=["testserver"])
class VuesEtApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("donnees_demo", stdout=open("/dev/null", "w"))
        User = get_user_model()
        cls.admin = User.objects.create_superuser("admin", password="x")
        cls.lecteur = User.objects.create_user("lecteur", password="x", role="lecture")
        cls.magasin = User.objects.create_user("magasin", password="x", role="magasin")

    def test_tableau_de_bord(self):
        self.assertEqual(self.client.get("/tableau-de-bord/").status_code, 302)
        self.client.force_login(self.admin)
        r = self.client.get("/tableau-de-bord/?centre=unipod-mali")
        self.assertContains(r, "Taux de disponibilité du parc")
        self.assertContains(r, "Cible")
        r = self.client.get("/rapports/indicateurs.csv")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Heures d'utilisation des machines", r.content.decode())

    def test_pages_admin(self):
        from django.contrib import admin

        self.client.force_login(self.admin)
        for modele in admin.site._registry:
            o = modele._meta
            url = f"/admin/{o.app_label}/{o.model_name}/"
            self.assertEqual(self.client.get(url).status_code, 200, url)
            self.assertEqual(self.client.get(url + "add/").status_code, 200, url)

    def test_api_permissions(self):
        self.assertEqual(self.client.get("/api/articles/").status_code, 403)
        self.client.force_login(self.lecteur)
        self.assertEqual(self.client.get("/api/articles/").status_code, 200)
        self.assertEqual(self.client.get("/api/indicateurs/").status_code, 200)
        article = Article.objects.first()
        r = self.client.post("/api/mouvements-stock/", {"article": article.pk, "type": "entree", "quantite": 1})
        self.assertEqual(r.status_code, 403)

    def test_api_mouvement_stock_et_regles_metier(self):
        self.client.force_login(self.magasin)
        article = Article.objects.get(reference="GANTS")
        r = self.client.post("/api/mouvements-stock/", {"article": article.pk, "type": "sortie", "quantite": 99})
        self.assertEqual(r.status_code, 400)
        self.assertIn("insuffisant", str(r.json()))
        r = self.client.post("/api/mouvements-stock/", {"article": article.pk, "type": "entree", "quantite": 4})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["cree_par"], self.magasin.pk)
        article.refresh_from_db()
        self.assertEqual(article.quantite, 5)
        mvt = r.json()["id"]
        self.assertEqual(self.client.patch(f"/api/mouvements-stock/{mvt}/", {}, content_type="application/json")
                         .status_code, 405)
