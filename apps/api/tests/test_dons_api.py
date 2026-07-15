import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.comptes.models import Paroisse, Utilisateur
from apps.finances.models import Don, RecuFiscal

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def creer_client(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    client = APIClient()
    client.force_authenticate(user=utilisateur)
    return client


def test_creer_un_don_via_l_api_genere_aussi_le_recu_fiscal(paroisse):
    client = creer_client(paroisse, "Trésorier", "tresorier1")

    reponse = client.post(
        reverse("api:don-list"),
        {"montant": "25.00", "date": "2026-03-01", "type_don": "offrande", "mode_paiement": "especes"},
    )

    assert reponse.status_code == 201
    assert reponse.data["recu_fiscal"]["numero"] == "REC-2026-0001"

    don = Don.objects.get(paroisse=paroisse)
    assert RecuFiscal.objects.filter(don=don).exists()


def test_secretaire_n_a_pas_acces_aux_dons(paroisse):
    client = creer_client(paroisse, "Secrétaire", "secretaire1")

    reponse = client.get(reverse("api:don-list"))

    assert reponse.status_code == 403
