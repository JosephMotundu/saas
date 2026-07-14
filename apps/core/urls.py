from django.urls import path

from .views import (
    AccueilView,
    FonctionnalitesView,
    InscriptionView,
    TableauDeBordView,
    TarifsView,
)

app_name = "core"

urlpatterns = [
    path("", AccueilView.as_view(), name="accueil"),
    path("fonctionnalites/", FonctionnalitesView.as_view(), name="fonctionnalites"),
    path("tarifs/", TarifsView.as_view(), name="tarifs"),
    path("souscription/", InscriptionView.as_view(), name="souscription"),
    path("tableau-de-bord/", TableauDeBordView.as_view(), name="tableau_de_bord"),
]
