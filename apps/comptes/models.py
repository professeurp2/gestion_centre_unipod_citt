"""Comptes utilisateurs et rôles d'accès à la plateforme."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """Utilisateur de la plateforme (membre du personnel ou administrateur).

    Les rôles sont matérialisés par des groupes Django (voir la commande
    ``init_roles``) ; le champ ``role`` sert de rôle principal affiché.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur plateforme"
        DIRECTION = "direction", "Direction du centre"
        RH = "rh", "Ressources humaines"
        TECHNIQUE = "technique", "Responsable technique / Fab manager"
        MAGASIN = "magasin", "Gestionnaire de stock"
        PROGRAMME = "programme", "Chargé de programmes"
        ACCUEIL = "accueil", "Accueil"
        LECTURE = "lecture", "Lecture seule"

    role = models.CharField("rôle principal", max_length=20, choices=Role.choices, default=Role.LECTURE)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    centre = models.ForeignKey(
        "core.Centre",
        verbose_name="centre de rattachement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="utilisateurs",
    )

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username

    # Correspondance rôle principal -> groupe de permissions (cf. ``init_unipod``).
    GROUPES_ROLES = {
        Role.DIRECTION: "Direction",
        Role.RH: "Ressources humaines",
        Role.TECHNIQUE: "Technique",
        Role.MAGASIN: "Magasin",
        Role.PROGRAMME: "Programmes",
        Role.ACCUEIL: "Accueil",
        Role.LECTURE: "Lecture seule",
    }

    def save(self, *args, **kwargs):
        # Tout compte de la plateforme accède à l'interface de gestion ;
        # ses droits effectifs dépendent du groupe associé à son rôle.
        if self.is_active:
            self.is_staff = True
        super().save(*args, **kwargs)
        self.synchroniser_groupe_role()

    def synchroniser_groupe_role(self):
        from django.contrib.auth.models import Group

        groupes_roles = Group.objects.filter(name__in=self.GROUPES_ROLES.values())
        self.groups.remove(*groupes_roles)
        nom = self.GROUPES_ROLES.get(self.role)
        if nom:
            groupe = groupes_roles.filter(name=nom).first()
            if groupe:
                self.groups.add(groupe)
