import requests
from django.conf import settings
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.celebrations.models import Celebration, IntentionMesse
from apps.communication.models import Annonce
from apps.finances.models import Don
from apps.finances.services import enregistrer_don_avec_recu
from apps.paroissiens.models import Paroissien

from .mixins import IsolationParoisseMixin
from .permissions import creer_permission_role
from .serializers import (
    AnnonceSerializer,
    CelebrationSerializer,
    DonSerializer,
    IntentionMesseSerializer,
    ParoisseSuspendueTokenObtainPairSerializer,
    ParoissienSerializer,
)


class ObtenirJetonView(TokenObtainPairView):
    serializer_class = ParoisseSuspendueTokenObtainPairSerializer


ROLES_PASTORALE_LECTURE = ("Secrétaire", "Lecteur")
ROLES_PASTORALE_ECRITURE = ("Secrétaire",)
ROLES_FINANCES_LECTURE = ("Trésorier", "Lecteur")
ROLES_FINANCES_ECRITURE = ("Trésorier",)


class ParoissienViewSet(IsolationParoisseMixin, viewsets.ModelViewSet):
    serializer_class = ParoissienSerializer
    queryset = Paroissien.objects.select_related("famille").order_by("nom", "prenom")
    permission_classes = [
        IsAuthenticated,
        creer_permission_role(ROLES_PASTORALE_LECTURE, ROLES_PASTORALE_ECRITURE),
    ]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}


class CelebrationViewSet(IsolationParoisseMixin, viewsets.ModelViewSet):
    serializer_class = CelebrationSerializer
    queryset = Celebration.objects.order_by("date", "heure")
    permission_classes = [
        IsAuthenticated,
        creer_permission_role(ROLES_PASTORALE_LECTURE, ROLES_PASTORALE_ECRITURE),
    ]


class IntentionMesseViewSet(IsolationParoisseMixin, viewsets.ModelViewSet):
    serializer_class = IntentionMesseSerializer
    queryset = IntentionMesse.objects.select_related("celebration")
    permission_classes = [
        IsAuthenticated,
        creer_permission_role(ROLES_PASTORALE_LECTURE, ROLES_PASTORALE_ECRITURE),
    ]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}


class DonViewSet(IsolationParoisseMixin, viewsets.ModelViewSet):
    """La création passe par services.enregistrer_don_avec_recu : un Don
    créé via l'API doit obtenir un reçu fiscal exactement comme depuis
    l'interface web, dans la même transaction atomique (§14 du brief)."""

    serializer_class = DonSerializer
    queryset = Don.objects.select_related("paroissien", "recu_fiscal")
    permission_classes = [
        IsAuthenticated,
        creer_permission_role(ROLES_FINANCES_LECTURE, ROLES_FINANCES_ECRITURE),
    ]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    def perform_create(self, serializer):
        donnees = serializer.validated_data
        don, _recu = enregistrer_don_avec_recu(
            paroisse=self.exiger_paroisse(),
            montant=donnees["montant"],
            date=donnees["date"],
            type_don=donnees["type_don"],
            mode_paiement=donnees["mode_paiement"],
            paroissien=donnees.get("paroissien"),
        )
        serializer.instance = don


class AnnonceViewSet(IsolationParoisseMixin, viewsets.ModelViewSet):
    serializer_class = AnnonceSerializer
    queryset = Annonce.objects.select_related("auteur", "groupe_cible")
    permission_classes = [
        IsAuthenticated,
        creer_permission_role(ROLES_PASTORALE_LECTURE, ROLES_PASTORALE_ECRITURE),
    ]

    def perform_create(self, serializer):
        serializer.save(paroisse=self.exiger_paroisse(), auteur=self.request.user)


class GeocoderParoisseView(APIView):
    """Consomme l'API Nominatim (OpenStreetMap) pour géocoder l'adresse de
    la paroisse courante et enregistrer ses coordonnées — ensuite affichées
    sur la carte Leaflet du tableau de bord (§6 du brief). Réservé au Curé :
    modifier la localisation officielle de la paroisse n'est pas une
    action de consultation courante."""

    permission_classes = [IsAuthenticated, creer_permission_role()]

    def post(self, request):
        paroisse = request.user.paroisse
        if paroisse is None:
            raise PermissionDenied(
                "Un superadministrateur n'a pas de paroisse à géocoder."
            )

        adresse = ", ".join(
            partie for partie in [paroisse.adresse, paroisse.ville, paroisse.diocese] if partie
        )
        try:
            reponse = requests.get(
                f"{settings.NOMINATIM_BASE_URL}/search",
                params={"q": adresse, "format": "json", "limit": 1},
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                timeout=5,
            )
            reponse.raise_for_status()
            resultats = reponse.json()
        except requests.RequestException as erreur:
            return Response(
                {"detail": f"Service de géocodage indisponible ({erreur})."}, status=503
            )

        if not resultats:
            return Response(
                {"detail": "Adresse introuvable auprès du service de géocodage."}, status=404
            )

        paroisse.latitude = resultats[0]["lat"]
        paroisse.longitude = resultats[0]["lon"]
        paroisse.save(update_fields=["latitude", "longitude"])

        return Response({"latitude": paroisse.latitude, "longitude": paroisse.longitude})


class GeocoderInverseView(APIView):
    """Géocodage inverse (coordonnées -> adresse), public : utilisé sur la
    page de souscription, avant la création de tout compte, pour que
    pointer sur la carte remplisse le champ adresse automatiquement plutôt
    que de multiplier les champs de saisie."""

    permission_classes = [AllowAny]

    def get(self, request):
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        if not lat or not lon:
            return Response({"detail": "Paramètres lat et lon requis."}, status=400)

        try:
            reponse = requests.get(
                f"{settings.NOMINATIM_BASE_URL}/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                timeout=5,
            )
            reponse.raise_for_status()
            resultat = reponse.json()
        except requests.RequestException as erreur:
            return Response(
                {"detail": f"Service de géocodage indisponible ({erreur})."}, status=503
            )

        if "error" in resultat:
            return Response({"detail": "Aucune adresse trouvée à cet endroit."}, status=404)

        composants = resultat.get("address", {})
        rue = " ".join(
            partie
            for partie in [composants.get("house_number"), composants.get("road")]
            if partie
        )
        ville = (
            composants.get("city")
            or composants.get("town")
            or composants.get("village")
            or composants.get("municipality")
            or ""
        )

        return Response(
            {
                "adresse": rue or resultat.get("display_name", ""),
                "ville": ville,
                "affichage": resultat.get("display_name", ""),
            }
        )
