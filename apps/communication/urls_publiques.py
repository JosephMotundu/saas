from django.urls import path

from .views import AnnoncePubliqueDetailView, AnnoncePubliqueListView

app_name = "communication_publique"

urlpatterns = [
    path("annonces/", AnnoncePubliqueListView.as_view(), name="annonce_liste"),
    path("annonces/<int:pk>/", AnnoncePubliqueDetailView.as_view(), name="annonce_detail"),
]
