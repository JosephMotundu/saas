from django.urls import path

from . import views

app_name = "finances"

urlpatterns = [
    path("", views.TableauFinancierView.as_view(), name="tableau"),
    path("dons/", views.DonListView.as_view(), name="don_liste"),
    path("dons/nouveau/", views.DonCreateView.as_view(), name="don_creer"),
    path("dons/<int:pk>/", views.DonDetailView.as_view(), name="don_detail"),
    path("dons/<int:pk>/recu/", views.RecuFiscalView.as_view(), name="recu_fiscal"),
    path("depenses/", views.DepenseListView.as_view(), name="depense_liste"),
    path("depenses/nouvelle/", views.DepenseCreateView.as_view(), name="depense_creer"),
    path("depenses/<int:pk>/", views.DepenseDetailView.as_view(), name="depense_detail"),
    path("offrandes-messe/", views.OffrandeMesseListView.as_view(), name="offrande_liste"),
    path("offrandes-messe/nouvelle/", views.OffrandeMesseCreateView.as_view(), name="offrande_creer"),
    path("offrandes-messe/<int:pk>/", views.OffrandeMesseDetailView.as_view(), name="offrande_detail"),
]
