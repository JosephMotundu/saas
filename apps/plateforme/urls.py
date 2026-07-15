from django.urls import path

from . import views

app_name = "plateforme"

urlpatterns = [
    path("", views.ParoisseListView.as_view(), name="paroisse_liste"),
    path("paroisses/<int:pk>/", views.ParoisseDetailView.as_view(), name="paroisse_detail"),
    path(
        "paroisses/<int:pk>/basculer-active/",
        views.ParoisseBasculerActiveView.as_view(),
        name="paroisse_basculer_active",
    ),
    path(
        "membres/<int:pk>/reinitialiser-mot-de-passe/",
        views.MembreReinitialiserMotDePasseView.as_view(),
        name="membre_reinitialiser_mot_de_passe",
    ),
    path("vitrine/", views.VitrineModifierView.as_view(), name="vitrine_modifier"),
]
