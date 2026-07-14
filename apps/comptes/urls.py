from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import ConnexionView

app_name = "comptes"

urlpatterns = [
    path("connexion/", ConnexionView.as_view(), name="connexion"),
    path(
        "deconnexion/",
        LogoutView.as_view(template_name="comptes/deconnexion.html"),
        name="deconnexion",
    ),
]
