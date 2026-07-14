from django.urls import path

from . import views

app_name = "paroissiens"

urlpatterns = [
    path("", views.ParoissienListView.as_view(), name="paroissien_liste"),
    path("nouveau/", views.ParoissienCreateView.as_view(), name="paroissien_creer"),
    path("<int:pk>/", views.ParoissienDetailView.as_view(), name="paroissien_detail"),
    path("<int:pk>/modifier/", views.ParoissienUpdateView.as_view(), name="paroissien_modifier"),
    path("<int:pk>/supprimer/", views.ParoissienDeleteView.as_view(), name="paroissien_supprimer"),
    path("familles/", views.FamilleListView.as_view(), name="famille_liste"),
    path("familles/nouvelle/", views.FamilleCreateView.as_view(), name="famille_creer"),
    path("familles/<int:pk>/", views.FamilleDetailView.as_view(), name="famille_detail"),
    path("familles/<int:pk>/modifier/", views.FamilleUpdateView.as_view(), name="famille_modifier"),
    path("familles/<int:pk>/supprimer/", views.FamilleDeleteView.as_view(), name="famille_supprimer"),
]
