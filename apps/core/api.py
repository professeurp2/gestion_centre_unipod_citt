"""Construction automatique de l'API REST des modules.

Chaque module déclare ses ressources dans son ``api.py`` via ``ressource(...)`` ;
ajouter un nouveau module à l'API ne demande donc que quelques lignes.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, viewsets

RESSOURCES = []


class BaseSerializer(serializers.ModelSerializer):
    """Applique les règles métier du modèle (``clean``) aux écritures API."""

    libelle = serializers.CharField(source="__str__", read_only=True)

    def validate(self, attrs):
        modele = self.Meta.model
        simples = {k: v for k, v in attrs.items() if not modele._meta.get_field(k).many_to_many}
        if self.instance is not None:
            obj = modele.objects.get(pk=self.instance.pk)
            for k, v in simples.items():
                setattr(obj, k, v)
        else:
            obj = modele(**simples)
        try:
            obj.clean()
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, "error_dict") else e.messages)
        return attrs


class BaseViewSet(viewsets.ModelViewSet):
    def perform_create(self, serializer):
        modele = serializer.Meta.model
        if any(f.name == "cree_par" for f in modele._meta.fields):
            serializer.save(cree_par=self.request.user)
        else:
            serializer.save()


def ressource(prefixe, modele, recherche=(), filtres=(), queryset=None, lecture_seule=False, ecriture_unique=False):
    """Déclare un endpoint ``/api/<prefixe>/`` pour ``modele``.

    ``ecriture_unique`` : création et lecture seulement (journaux immuables).
    """
    Serializer = type(
        f"{modele.__name__}Serializer",
        (BaseSerializer,),
        {"Meta": type("Meta", (), {"model": modele, "fields": "__all__"})},
    )
    attrs = {
        "queryset": queryset if queryset is not None else modele.objects.all(),
        "serializer_class": Serializer,
        "search_fields": list(recherche),
        "filterset_fields": list(filtres),
    }
    if lecture_seule:
        attrs["http_method_names"] = ["get", "head", "options"]
    elif ecriture_unique:
        attrs["http_method_names"] = ["get", "post", "head", "options"]
    ViewSet = type(f"{modele.__name__}ViewSet", (BaseViewSet,), attrs)
    RESSOURCES.append((prefixe, ViewSet))
    return ViewSet
