import pytest
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


def test_page_connexion_accessible(client):
    reponse = client.get(reverse("comptes:connexion"))

    assert reponse.status_code == 200
    assert "ParoisseConnect" in reponse.content.decode()


def test_connexion_avec_identifiants_valides(client):
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )

    reponse = client.post(
        reverse("comptes:connexion"),
        {"username": "secretaire1", "password": "mot-de-passe-test-123"},
    )

    assert reponse.status_code == 302

def test_deconnexion_accessible(client):
    reponse = client.post(reverse("comptes:deconnexion"))

    assert reponse.status_code == 200
    assert "session a été fermée" in reponse.content.decode()
