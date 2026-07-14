from django.urls import path

from . import views

app_name = "communication"

urlpatterns = [
    path("", views.AnnonceListView.as_view(), name="annonce_liste"),
    path("nouvelle/", views.AnnonceCreateView.as_view(), name="annonce_creer"),
    path("<int:pk>/", views.AnnonceDetailView.as_view(), name="annonce_detail"),
    path("<int:pk>/modifier/", views.AnnonceUpdateView.as_view(), name="annonce_modifier"),
    path("<int:pk>/supprimer/", views.AnnonceDeleteView.as_view(), name="annonce_supprimer"),
]
