from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from apps.core import api_ressources  # noqa: F401  (enregistre les ressources)
from apps.core.api import RESSOURCES
from apps.rapports import views as rapports

routeur = DefaultRouter()
for prefixe, viewset in RESSOURCES:
    routeur.register(prefixe, viewset, basename=prefixe)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tableau-de-bord", permanent=False)),
    path("tableau-de-bord/", rapports.tableau_de_bord, name="tableau-de-bord"),
    path("rapports/indicateurs.csv", rapports.export_indicateurs_csv, name="export-indicateurs"),
    path("api/indicateurs/", rapports.api_indicateurs, name="api-indicateurs"),
    path("api/", include(routeur.urls)),
    path("api/auth/", include("rest_framework.urls")),
    path("admin/", admin.site.urls),
]
