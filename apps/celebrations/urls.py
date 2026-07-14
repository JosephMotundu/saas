from django.urls import path

from . import views

app_name = "celebrations"

urlpatterns = [
    path("", views.CelebrationListView.as_view(), name="celebration_liste"),
    path("nouvelle/", views.CelebrationCreateView.as_view(), name="celebration_creer"),
    path("<int:pk>/", views.CelebrationDetailView.as_view(), name="celebration_detail"),
    path(
        "<int:pk>/modifier/",
        views.CelebrationUpdateView.as_view(),
        name="celebration_modifier",
    ),
    path("intentions/", views.IntentionMesseListView.as_view(), name="intention_liste"),
    path(
        "intentions/nouvelle/",
        views.IntentionMesseCreateView.as_view(),
        name="intention_creer",
    ),
    path(
        "intentions/<int:pk>/",
        views.IntentionMesseDetailView.as_view(),
        name="intention_detail",
    ),
    path(
        "intentions/<int:pk>/modifier/",
        views.IntentionMesseUpdateView.as_view(),
        name="intention_modifier",
    ),
]
