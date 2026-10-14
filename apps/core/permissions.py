from rest_framework.permissions import DjangoModelPermissions


class PermissionsModele(DjangoModelPermissions):
    """Permissions Django par modèle, y compris pour la lecture (``view``)."""

    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
    }
