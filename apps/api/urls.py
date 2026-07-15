from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AnnonceViewSet,
    CelebrationViewSet,
    DonViewSet,
    GeocoderParoisseView,
    IntentionMesseViewSet,
    ObtenirJetonView,
    ParoissienViewSet,
)

app_name = "api"

router = DefaultRouter()
router.register("paroissiens", ParoissienViewSet, basename="paroissien")
router.register("celebrations", CelebrationViewSet, basename="celebration")
router.register("intentions", IntentionMesseViewSet, basename="intention")
router.register("dons", DonViewSet, basename="don")
router.register("annonces", AnnonceViewSet, basename="annonce")

urlpatterns = [
    path("jeton/", ObtenirJetonView.as_view(), name="jeton_obtenir"),
    path("jeton/rafraichir/", TokenRefreshView.as_view(), name="jeton_rafraichir"),
    path("paroisse/geocoder/", GeocoderParoisseView.as_view(), name="paroisse_geocoder"),
    path("", include(router.urls)),
]
