from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.stocks.models import Commande, Fournisseur, LigneCommande, MouvementStock

from . import fabriques as F


class MouvementStockTests(TestCase):
    def setUp(self):
        self.article = F.article()

    def test_entree_et_sortie_mettent_a_jour_le_stock(self):
        MouvementStock.objects.create(article=self.article, type="entree", quantite=10)
        MouvementStock.objects.create(article=self.article, type="sortie", quantite=3)
        MouvementStock.objects.create(article=self.article, type="perte", quantite=1)
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantite, Decimal("6"))
        self.assertEqual(self.article.recalculer_quantite(), Decimal("6"))

    def test_stock_negatif_interdit(self):
        MouvementStock.objects.create(article=self.article, type="entree", quantite=2)
        with self.assertRaises(ValidationError):
            MouvementStock.objects.create(article=self.article, type="sortie", quantite=5)
        self.article.refresh_from_db()
        self.assertEqual(self.article.quantite, Decimal("2"))

    def test_clean_signale_stock_insuffisant(self):
        m = MouvementStock(article=self.article, type="sortie", quantite=1)
        with self.assertRaises(ValidationError):
            m.full_clean()

    def test_mouvement_immuable(self):
        m = MouvementStock.objects.create(article=self.article, type="entree", quantite=2)
        m.quantite = 50
        with self.assertRaises(ValidationError):
            m.save()

    def test_alerte_seuil(self):
        MouvementStock.objects.create(article=self.article, type="entree", quantite=2)
        self.article.refresh_from_db()
        self.assertTrue(self.article.en_alerte)
        MouvementStock.objects.create(article=self.article, type="entree", quantite=1)
        self.article.refresh_from_db()
        self.assertFalse(self.article.en_alerte)


class CommandeTests(TestCase):
    def test_reception_genere_les_entrees_une_seule_fois(self):
        article = F.article()
        commande = Commande.objects.create(
            centre=article.centre, numero="BC-1", fournisseur=Fournisseur.objects.create(nom="F1")
        )
        ligne = LigneCommande.objects.create(commande=commande, article=article, quantite=12, prix_unitaire=500)
        self.assertEqual(commande.montant_total, Decimal("6000"))
        commande.receptionner()
        commande.receptionner()  # idempotent : rien de plus à recevoir
        article.refresh_from_db()
        self.assertEqual(article.quantite, Decimal("12"))
        self.assertEqual(ligne.quantite_restante, 0)
        self.assertEqual(commande.statut, Commande.Statut.RECUE)
