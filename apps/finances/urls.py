from django.urls import path

from . import views

app_name = "finances"

urlpatterns = [
    path("", views.DonListView.as_view(), name="don_liste"),
    path("nouveau/", views.DonCreateView.as_view(), name="don_creer"),
    path("<int:pk>/", views.DonDetailView.as_view(), name="don_detail"),
    path("<int:pk>/recu/", views.RecuFiscalView.as_view(), name="recu_fiscal"),
]
