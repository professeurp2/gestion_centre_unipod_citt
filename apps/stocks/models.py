"""Stocks : consommables, pièces détachées, fournisseurs, mouvements et commandes.

Le stock d'un article n'est jamais saisi directement : il résulte des
``MouvementStock`` (entrées, sorties, ajustements), ce qui garantit une
traçabilité complète.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.core.models import Centre, Espace, Horodatage, Tracabilite


class Fournisseur(Horodatage):
    nom = models.CharField("raison sociale", max_length=200, unique=True)
    contact = models.CharField("contact", max_length=150, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("e-mail", blank=True)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    pays = models.CharField("pays", max_length=80, default="Mali")
    nif = models.CharField("NIF", max_length=40, blank=True)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "fournisseur"
        verbose_name_plural = "fournisseurs"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class CategorieArticle(models.Model):
    nom = models.CharField("nom", max_length=120, unique=True)
    description = models.TextField("description", blank=True)

    class Meta:
        verbose_name = "catégorie d'article"
        verbose_name_plural = "catégories d'articles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Article(Horodatage):
    """Consommable ou pièce gérée en stock (filament, bois, composants, EPI…)."""

    class Unite(models.TextChoices):
        PIECE = "piece", "pièce(s)"
        KG = "kg", "kg"
        G = "g", "g"
        M = "m", "mètre(s)"
        M2 = "m2", "m²"
        L = "l", "litre(s)"
        ROULEAU = "rouleau", "rouleau(x)"
        BOBINE = "bobine", "bobine(s)"
        PLAQUE = "plaque", "plaque(s)"
        BOITE = "boite", "boîte(s)"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="articles")
    reference = models.CharField("référence", max_length=40)
    designation = models.CharField("désignation", max_length=200)
    categorie = models.ForeignKey(CategorieArticle, verbose_name="catégorie", on_delete=models.PROTECT)
    unite = models.CharField("unité", max_length=10, choices=Unite.choices, default=Unite.PIECE)
    quantite = models.DecimalField("quantité en stock", max_digits=12, decimal_places=2, default=0, editable=False)
    seuil_alerte = models.DecimalField("seuil d'alerte", max_digits=12, decimal_places=2, default=0)
    prix_unitaire = models.DecimalField("prix unitaire (FCFA)", max_digits=12, decimal_places=0, default=0)
    emplacement = models.ForeignKey(Espace, on_delete=models.SET_NULL, null=True, blank=True)
    fournisseur_habituel = models.ForeignKey(Fournisseur, on_delete=models.SET_NULL, null=True, blank=True)
    actif = models.BooleanField("actif", default=True)

    class Meta:
        verbose_name = "article"
        verbose_name_plural = "articles"
        ordering = ["designation"]
        constraints = [
            models.UniqueConstraint(fields=["centre", "reference"], name="article_reference_unique_par_centre"),
        ]

    def __str__(self):
        return f"{self.reference} — {self.designation}"

    @property
    def en_alerte(self):
        return self.quantite <= self.seuil_alerte

    @property
    def valeur_stock(self):
        return self.quantite * self.prix_unitaire

    def recalculer_quantite(self):
        """Recalcule le stock à partir de l'historique des mouvements (contrôle d'intégrité)."""
        total = self.mouvements.aggregate(t=Sum("quantite_signee"))["t"] or Decimal("0")
        Article.objects.filter(pk=self.pk).update(quantite=total)
        self.quantite = total
        return total


class MouvementStock(Tracabilite):
    class Type(models.TextChoices):
        ENTREE = "entree", "Entrée (réception / don)"
        SORTIE = "sortie", "Sortie (consommation)"
        AJUST_PLUS = "ajust_plus", "Ajustement inventaire (+)"
        AJUST_MOINS = "ajust_moins", "Ajustement inventaire (−)"
        PERTE = "perte", "Perte / casse / péremption"

    TYPES_SORTANTS = (Type.SORTIE, Type.AJUST_MOINS, Type.PERTE)

    article = models.ForeignKey(Article, on_delete=models.PROTECT, related_name="mouvements")
    type = models.CharField("type", max_length=20, choices=Type.choices)
    quantite = models.DecimalField("quantité", max_digits=12, decimal_places=2)
    quantite_signee = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    date = models.DateTimeField("date", default=timezone.now)
    motif = models.CharField("motif / observation", max_length=255, blank=True)
    usager = models.ForeignKey(
        "usagers.Usager", verbose_name="bénéficiaire", on_delete=models.SET_NULL, null=True, blank=True
    )
    projet = models.ForeignKey("programmes.Projet", on_delete=models.SET_NULL, null=True, blank=True)
    maintenance = models.ForeignKey("equipements.Maintenance", on_delete=models.SET_NULL, null=True, blank=True)
    ligne_commande = models.ForeignKey(
        "LigneCommande", on_delete=models.SET_NULL, null=True, blank=True, related_name="mouvements"
    )

    class Meta:
        verbose_name = "mouvement de stock"
        verbose_name_plural = "mouvements de stock"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()} {self.quantite} {self.article.get_unite_display()} — {self.article}"

    def clean(self):
        if self.quantite is not None and self.quantite <= 0:
            raise ValidationError({"quantite": "La quantité doit être strictement positive."})
        if self.pk is None and self.article_id and self.type in self.TYPES_SORTANTS and self.quantite:
            if self.quantite > self.article.quantite:
                raise ValidationError(
                    {"quantite": f"Stock insuffisant : {self.article.quantite} disponible(s)."}
                )

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError("Un mouvement de stock ne peut pas être modifié ; saisissez un ajustement.")
        self.quantite_signee = -self.quantite if self.type in self.TYPES_SORTANTS else self.quantite
        with transaction.atomic():
            article = Article.objects.select_for_update().get(pk=self.article_id)
            if article.quantite + self.quantite_signee < 0:
                raise ValidationError(f"Stock insuffisant pour {article} : {article.quantite} disponible(s).")
            super().save(*args, **kwargs)
            Article.objects.filter(pk=article.pk).update(quantite=F("quantite") + self.quantite_signee)
        self.article.refresh_from_db(fields=["quantite"])


class Commande(Tracabilite):
    """Bon de commande fournisseur."""

    class Statut(models.TextChoices):
        BROUILLON = "brouillon", "Brouillon"
        ENVOYEE = "envoyee", "Envoyée"
        PARTIELLE = "partielle", "Reçue partiellement"
        RECUE = "recue", "Reçue"
        ANNULEE = "annulee", "Annulée"

    centre = models.ForeignKey(Centre, on_delete=models.PROTECT, related_name="commandes")
    numero = models.CharField("numéro", max_length=30, unique=True)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, related_name="commandes")
    date_commande = models.DateField("date de commande", default=timezone.localdate)
    date_livraison_prevue = models.DateField("livraison prévue", null=True, blank=True)
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.BROUILLON)
    ligne_budgetaire = models.CharField("ligne budgétaire / bailleur", max_length=150, blank=True)
    observation = models.TextField("observation", blank=True)

    class Meta:
        verbose_name = "commande fournisseur"
        verbose_name_plural = "commandes fournisseurs"
        ordering = ["-date_commande"]

    def __str__(self):
        return f"{self.numero} — {self.fournisseur}"

    @property
    def montant_total(self):
        return sum((l.montant for l in self.lignes.all()), Decimal("0"))

    @transaction.atomic
    def receptionner(self, utilisateur=None):
        """Enregistre l'entrée en stock des quantités restant à recevoir."""
        for ligne in self.lignes.select_related("article"):
            reste = ligne.quantite_restante
            if reste > 0:
                MouvementStock.objects.create(
                    article=ligne.article,
                    type=MouvementStock.Type.ENTREE,
                    quantite=reste,
                    motif=f"Réception commande {self.numero}",
                    ligne_commande=ligne,
                    cree_par=utilisateur,
                )
        self.statut = self.Statut.RECUE
        self.save(update_fields=["statut", "modifie_le"])


class LigneCommande(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name="lignes")
    article = models.ForeignKey(Article, on_delete=models.PROTECT)
    quantite = models.DecimalField("quantité commandée", max_digits=12, decimal_places=2)
    prix_unitaire = models.DecimalField("prix unitaire (FCFA)", max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "ligne de commande"
        verbose_name_plural = "lignes de commande"

    def __str__(self):
        return f"{self.article} × {self.quantite}"

    @property
    def montant(self):
        return (self.quantite or 0) * (self.prix_unitaire or 0)

    @property
    def quantite_recue(self):
        return self.mouvements.aggregate(t=Sum("quantite"))["t"] or Decimal("0")

    @property
    def quantite_restante(self):
        return max(self.quantite - self.quantite_recue, Decimal("0"))
