import pytest
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


@pytest.fixture
def cure(paroisse):
    return Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )


def test_connexion_refusee_si_paroisse_suspendue(client, paroisse, cure):
    paroisse.est_active = False
    paroisse.save()

    reponse = client.post(
        reverse("comptes:connexion"), {"username": "cure1", "password": "mot-de-passe-test-123"}
    )

    assert reponse.status_code == 200
    assert "suspendue" in reponse.content.decode().lower()
    assert "_auth_user_id" not in client.session


def test_connexion_normale_si_paroisse_active(client, paroisse, cure):
    reponse = client.post(
        reverse("comptes:connexion"), {"username": "cure1", "password": "mot-de-passe-test-123"}
    )

    assert reponse.status_code == 302


def test_session_ouverte_coupee_des_que_la_paroisse_est_suspendue(client, paroisse, cure):
    client.force_login(cure)
    assert client.get(reverse("core:tableau_de_bord")).status_code == 200

    paroisse.est_active = False
    paroisse.save()

    reponse = client.get(reverse("core:tableau_de_bord"))

    assert reponse.status_code == 302
    assert reponse.url == reverse("comptes:connexion")
    assert "_auth_user_id" not in client.session


def test_reactivation_restaure_l_acces(client, paroisse, cure):
    paroisse.est_active = False
    paroisse.save()
    client.post(
        reverse("comptes:connexion"), {"username": "cure1", "password": "mot-de-passe-test-123"}
    )

    paroisse.est_active = True
    paroisse.save()
    reponse = client.post(
        reverse("comptes:connexion"), {"username": "cure1", "password": "mot-de-passe-test-123"}
    )

    assert reponse.status_code == 302
