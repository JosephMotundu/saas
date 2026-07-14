from django.contrib.auth.views import LogoutView, PasswordChangeDoneView, PasswordChangeView
from django.urls import path, reverse_lazy

from .views import (
    AbonnementBasculerStatutView,
    AbonnementView,
    ConnexionView,
    EquipeListView,
    InvitationCreateView,
    MembreBasculerActifView,
    ProfilModifierView,
    ProfilView,
)

app_name = "comptes"

urlpatterns = [
    path("connexion/", ConnexionView.as_view(), name="connexion"),
    path(
        "deconnexion/",
        LogoutView.as_view(template_name="comptes/deconnexion.html"),
        name="deconnexion",
    ),
    path("profil/", ProfilView.as_view(), name="profil"),
    path("profil/modifier/", ProfilModifierView.as_view(), name="profil_modifier"),
    path(
        "profil/mot-de-passe/",
        PasswordChangeView.as_view(
            template_name="comptes/mot_de_passe_modifier.html",
            success_url=reverse_lazy("comptes:mot_de_passe_modifie"),
        ),
        name="mot_de_passe_modifier",
    ),
    path(
        "profil/mot-de-passe/termine/",
        PasswordChangeDoneView.as_view(template_name="comptes/mot_de_passe_modifie.html"),
        name="mot_de_passe_modifie",
    ),
    path("equipe/", EquipeListView.as_view(), name="equipe"),
    path("equipe/inviter/", InvitationCreateView.as_view(), name="equipe_inviter"),
    path(
        "equipe/<int:pk>/basculer-actif/",
        MembreBasculerActifView.as_view(),
        name="equipe_basculer_actif",
    ),
    path("abonnement/", AbonnementView.as_view(), name="abonnement"),
    path(
        "abonnement/basculer-statut/",
        AbonnementBasculerStatutView.as_view(),
        name="abonnement_basculer_statut",
    ),
]
