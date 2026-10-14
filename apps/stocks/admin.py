from django.contrib import admin, messages
from django.db.models import F

from apps.core.admin_utils import BaseAdmin

from .models import Article, CategorieArticle, Commande, Fournisseur, LigneCommande, MouvementStock


@admin.register(Fournisseur)
class FournisseurAdmin(BaseAdmin):
    list_display = ("nom", "contact", "telephone", "email", "pays", "actif")
    list_filter = ("pays", "actif")
    search_fields = ("nom", "contact", "nif")


@admin.register(CategorieArticle)
class CategorieArticleAdmin(BaseAdmin):
    search_fields = ("nom",)


class EnAlerteFilter(admin.SimpleListFilter):
    title = "niveau de stock"
    parameter_name = "alerte"

    def lookups(self, request, model_admin):
        return [("oui", "Sous le seuil d'alerte"), ("non", "Stock suffisant")]

    def queryset(self, request, queryset):
        if self.value() == "oui":
            return queryset.filter(quantite__lte=F("seuil_alerte"))
        if self.value() == "non":
            return queryset.filter(quantite__gt=F("seuil_alerte"))
        return queryset


class MouvementInline(admin.TabularInline):
    model = MouvementStock
    fk_name = "article"
    extra = 0
    fields = ("date", "type", "quantite", "motif", "cree_par")
    readonly_fields = fields
    can_delete = False
    ordering = ("-date",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Article)
class ArticleAdmin(BaseAdmin):
    list_display = ("reference", "designation", "categorie", "quantite", "unite", "seuil_alerte", "alerte", "prix_unitaire")
    list_filter = ("centre", "categorie", EnAlerteFilter, "actif")
    search_fields = ("reference", "designation")
    autocomplete_fields = ("categorie", "fournisseur_habituel", "emplacement")
    readonly_fields = ("quantite", "valeur_stock")
    inlines = [MouvementInline]

    @admin.display(boolean=True, description="OK")
    def alerte(self, obj):
        return not obj.en_alerte


@admin.register(MouvementStock)
class MouvementStockAdmin(BaseAdmin):
    list_display = ("date", "article", "type", "quantite", "usager", "projet", "cree_par")
    list_filter = ("type", "article__centre", "article__categorie")
    search_fields = ("article__designation", "article__reference", "motif")
    autocomplete_fields = ("article", "usager", "projet", "maintenance")
    readonly_fields = ("cree_par", "ligne_commande")
    date_hierarchy = "date"

    def has_change_permission(self, request, obj=None):
        # Les mouvements sont immuables : la consultation reste possible.
        return obj is None and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 1
    autocomplete_fields = ("article",)
    fields = ("article", "quantite", "prix_unitaire", "montant", "quantite_recue")
    readonly_fields = ("montant", "quantite_recue")


@admin.action(description="Réceptionner (entrée en stock)")
def receptionner(modeladmin, request, queryset):
    for commande in queryset.exclude(statut__in=[Commande.Statut.RECUE, Commande.Statut.ANNULEE]):
        commande.receptionner(request.user)
        messages.success(request, f"Commande {commande.numero} réceptionnée.")


@admin.register(Commande)
class CommandeAdmin(BaseAdmin):
    list_display = ("numero", "fournisseur", "date_commande", "date_livraison_prevue", "statut", "montant_total")
    list_filter = ("statut", "centre", "fournisseur")
    search_fields = ("numero", "fournisseur__nom")
    autocomplete_fields = ("fournisseur",)
    inlines = [LigneCommandeInline]
    actions = BaseAdmin.actions + [receptionner]
    date_hierarchy = "date_commande"
