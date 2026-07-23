from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.celebrations.models import Celebration, IntentionMesse
from apps.communication.models import Annonce
from apps.finances.models import Don, RecuFiscal
from apps.paroissiens.models import Famille, Paroissien


class ParoisseSuspendueTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Empêche l'émission d'un jeton JWT pour un compte dont la paroisse a
    été suspendue par la plateforme — même contrôle que ConnexionForm côté
    web (apps.comptes.forms)."""

    def validate(self, attrs):
        donnees = super().validate(attrs)
        paroisse = self.user.paroisse
        if paroisse is not None and not paroisse.est_active:
            raise AuthenticationFailed(
                "Votre paroisse a été suspendue. Contactez l'administrateur de "
                "la plateforme.",
                code="paroisse_suspendue",
            )
        return donnees


class ParoissienSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paroissien
        fields = [
            "id",
            "nom",
            "prenom",
            "sexe",
            "date_naissance",
            "adresse",
            "telephone",
            "email",
            "photo",
            "famille",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["famille"].queryset = Famille.objects.filter(
                paroisse=request.user.paroisse
            )


class CelebrationSerializer(serializers.ModelSerializer):
    type_celebration_affiche = serializers.CharField(
        source="get_type_celebration_display", read_only=True
    )

    class Meta:
        model = Celebration
        fields = [
            "id",
            "date",
            "heure",
            "type_celebration",
            "type_celebration_affiche",
            "celebrant",
            "lieu",
        ]


class IntentionMesseSerializer(serializers.ModelSerializer):
    statut_affiche = serializers.CharField(source="get_statut_display", read_only=True)

    class Meta:
        model = IntentionMesse
        fields = [
            "id",
            "demandeur",
            "intention",
            "montant_offrande",
            "devise",
            "statut",
            "statut_affiche",
            "celebration",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["celebration"].queryset = Celebration.objects.filter(
                paroisse=request.user.paroisse
            )


class RecuFiscalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecuFiscal
        fields = ["numero", "date_emission"]


class DonSerializer(serializers.ModelSerializer):
    recu_fiscal = RecuFiscalSerializer(read_only=True)

    class Meta:
        model = Don
        fields = [
            "id",
            "paroissien",
            "montant",
            "devise",
            "date",
            "type_don",
            "mode_paiement",
            "recu_fiscal",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request is not None and request.user.is_authenticated:
            self.fields["paroissien"].queryset = Paroissien.objects.filter(
                paroisse=request.user.paroisse
            )
        self.fields["paroissien"].required = False
        self.fields["paroissien"].allow_null = True


class AnnonceSerializer(serializers.ModelSerializer):
    auteur = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Annonce
        fields = [
            "id",
            "titre",
            "contenu",
            "date_publication",
            "auteur",
            "groupe_cible",
        ]
