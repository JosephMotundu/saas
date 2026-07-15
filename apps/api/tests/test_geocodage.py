from unittest.mock import Mock, patch

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël",
        diocese="Kinshasa",
        adresse="Boulevard du 30 Juin",
        ville="Kinshasa",
    )


@pytest.fixture
def cure(paroisse):
    utilisateur = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur.groups.add(Group.objects.get(name="Curé"))
    return utilisateur


def _client_pour(utilisateur):
    client = APIClient()
    client.force_authenticate(user=utilisateur)
    return client


@patch("apps.api.views.requests.get")
def test_geocodage_enregistre_les_coordonnees(requests_get, paroisse, cure):
    requests_get.return_value = Mock(
        status_code=200,
        json=lambda: [{"lat": "-4.305737", "lon": "15.302001"}],
        raise_for_status=lambda: None,
    )
    client = _client_pour(cure)

    reponse = client.post(reverse("api:paroisse_geocoder"))

    assert reponse.status_code == 200
    paroisse.refresh_from_db()
    assert str(paroisse.latitude) == "-4.305737"
    assert str(paroisse.longitude) == "15.302001"
    # L'appel a bien inclus un User-Agent, requis par la politique d'usage
    # de Nominatim.
    assert "User-Agent" in requests_get.call_args.kwargs["headers"]


@patch("apps.api.views.requests.get")
def test_geocodage_adresse_introuvable(requests_get, paroisse, cure):
    requests_get.return_value = Mock(
        status_code=200, json=lambda: [], raise_for_status=lambda: None
    )
    client = _client_pour(cure)

    reponse = client.post(reverse("api:paroisse_geocoder"))

    assert reponse.status_code == 404


def test_geocodage_reserve_au_cure(paroisse):
    secretaire = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    secretaire.groups.add(Group.objects.get(name="Secrétaire"))
    client = _client_pour(secretaire)

    reponse = client.post(reverse("api:paroisse_geocoder"))

    assert reponse.status_code == 403


@patch("apps.api.views.requests.get")
def test_geocodage_inverse_est_public_et_renvoie_l_adresse(requests_get):
    requests_get.return_value = Mock(
        status_code=200,
        json=lambda: {
            "address": {
                "house_number": "44/A",
                "road": "Boulevard du 30 Juin",
                "city": "Golf",
            },
            "display_name": "44/A, Boulevard du 30 Juin, Golf, Kinshasa, RDC",
        },
        raise_for_status=lambda: None,
    )
    client = APIClient()

    reponse = client.get(
        reverse("api:geocoder_inverse"), {"lat": "-4.305737", "lon": "15.302001"}
    )

    assert reponse.status_code == 200
    assert reponse.data["adresse"] == "44/A Boulevard du 30 Juin"
    assert reponse.data["ville"] == "Golf"


@patch("apps.api.views.requests.get")
def test_geocodage_inverse_adresse_introuvable(requests_get):
    requests_get.return_value = Mock(
        status_code=200, json=lambda: {"error": "Unable to geocode"}, raise_for_status=lambda: None
    )
    client = APIClient()

    reponse = client.get(
        reverse("api:geocoder_inverse"), {"lat": "0", "lon": "0"}
    )

    assert reponse.status_code == 404


def test_geocodage_inverse_exige_lat_et_lon():
    client = APIClient()

    reponse = client.get(reverse("api:geocoder_inverse"))

    assert reponse.status_code == 400
