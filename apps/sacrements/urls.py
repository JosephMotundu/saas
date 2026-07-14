from django.urls import path

from . import views

app_name = "sacrements"

urlpatterns = [
    path("", views.SacrementsIndexView.as_view(), name="index"),
    # Baptêmes
    path("baptemes/", views.BaptemeListView.as_view(), name="bapteme_liste"),
    path("baptemes/nouveau/", views.BaptemeCreateView.as_view(), name="bapteme_creer"),
    path("baptemes/<int:pk>/", views.BaptemeDetailView.as_view(), name="bapteme_detail"),
    path(
        "baptemes/<int:pk>/modifier/",
        views.BaptemeUpdateView.as_view(),
        name="bapteme_modifier",
    ),
    path(
        "baptemes/<int:pk>/certificat/",
        views.BaptemeCertificatView.as_view(),
        name="bapteme_certificat",
    ),
    path(
        "baptemes/<int:pk>/mentions/ajouter/",
        views.MentionMarginaleCreateView.as_view(),
        name="mention_marginale_creer",
    ),
    # Communions
    path("communions/", views.CommunionListView.as_view(), name="communion_liste"),
    path("communions/nouvelle/", views.CommunionCreateView.as_view(), name="communion_creer"),
    path("communions/<int:pk>/", views.CommunionDetailView.as_view(), name="communion_detail"),
    path(
        "communions/<int:pk>/modifier/",
        views.CommunionUpdateView.as_view(),
        name="communion_modifier",
    ),
    path(
        "communions/<int:pk>/certificat/",
        views.CommunionCertificatView.as_view(),
        name="communion_certificat",
    ),
    # Confirmations
    path("confirmations/", views.ConfirmationListView.as_view(), name="confirmation_liste"),
    path(
        "confirmations/nouvelle/",
        views.ConfirmationCreateView.as_view(),
        name="confirmation_creer",
    ),
    path(
        "confirmations/<int:pk>/",
        views.ConfirmationDetailView.as_view(),
        name="confirmation_detail",
    ),
    path(
        "confirmations/<int:pk>/modifier/",
        views.ConfirmationUpdateView.as_view(),
        name="confirmation_modifier",
    ),
    path(
        "confirmations/<int:pk>/certificat/",
        views.ConfirmationCertificatView.as_view(),
        name="confirmation_certificat",
    ),
    # Funérailles
    path("funerailles/", views.FunraillesListView.as_view(), name="funerailles_liste"),
    path(
        "funerailles/nouvelles/", views.FunraillesCreateView.as_view(), name="funerailles_creer"
    ),
    path(
        "funerailles/<int:pk>/", views.FunraillesDetailView.as_view(), name="funerailles_detail"
    ),
    path(
        "funerailles/<int:pk>/modifier/",
        views.FunraillesUpdateView.as_view(),
        name="funerailles_modifier",
    ),
    path(
        "funerailles/<int:pk>/certificat/",
        views.FunraillesCertificatView.as_view(),
        name="funerailles_certificat",
    ),
    # Mariages
    path("mariages/", views.MariageListView.as_view(), name="mariage_liste"),
    path("mariages/nouveau/", views.MariageCreateView.as_view(), name="mariage_creer"),
    path("mariages/<int:pk>/", views.MariageDetailView.as_view(), name="mariage_detail"),
    path(
        "mariages/<int:pk>/modifier/",
        views.MariageUpdateView.as_view(),
        name="mariage_modifier",
    ),
    path(
        "mariages/<int:pk>/certificat/",
        views.MariageCertificatView.as_view(),
        name="mariage_certificat",
    ),
]
