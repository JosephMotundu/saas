import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


@pytest.fixture
def secretaire(paroisse):
    from django.contrib.auth.models import Group

    utilisateur = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur.groups.add(Group.objects.get(name="Secrétaire"))
    return utilisateur


def test_obtenir_un_jeton_avec_des_identifiants_valides(secretaire):
    client = APIClient()

    reponse = client.post(
        reverse("api:jeton_obtenir"),
        {"username": "secretaire1", "password": "mot-de-passe-test-123"},
    )

    assert reponse.status_code == 200
    assert "access" in reponse.data
    assert "refresh" in reponse.data


def test_jeton_refuse_avec_un_mauvais_mot_de_passe(secretaire):
    client = APIClient()

    reponse = client.post(
        reverse("api:jeton_obtenir"),
        {"username": "secretaire1", "password": "mauvais-mot-de-passe"},
    )

    assert reponse.status_code == 401


def test_le_jeton_permet_d_accéder_a_un_endpoint_protege(secretaire):
    client = APIClient()
    jeton = client.post(
        reverse("api:jeton_obtenir"),
        {"username": "secretaire1", "password": "mot-de-passe-test-123"},
    ).data["access"]

    reponse_sans_jeton = client.get(reverse("api:paroissien-list"))
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")
    reponse_avec_jeton = client.get(reverse("api:paroissien-list"))

    assert reponse_sans_jeton.status_code == 401
    assert reponse_avec_jeton.status_code == 200


def test_jeton_refuse_si_la_paroisse_est_suspendue(paroisse, secretaire):
    paroisse.est_active = False
    paroisse.save()
    client = APIClient()

    reponse = client.post(
        reverse("api:jeton_obtenir"),
        {"username": "secretaire1", "password": "mot-de-passe-test-123"},
    )

    assert reponse.status_code == 401


def test_jeton_deja_emis_refuse_apres_suspension(paroisse, secretaire):
    client = APIClient()
    jeton = client.post(
        reverse("api:jeton_obtenir"),
        {"username": "secretaire1", "password": "mot-de-passe-test-123"},
    ).data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {jeton}")

    paroisse.est_active = False
    paroisse.save()
    reponse = client.get(reverse("api:paroissien-list"))

    assert reponse.status_code == 403
