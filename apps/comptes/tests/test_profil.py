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
def utilisateur(paroisse):
    return Utilisateur.objects.create_user(
        username="secretaire1",
        password="mot-de-passe-test-123",
        paroisse=paroisse,
        first_name="Marie",
        last_name="Kalonji",
    )


def test_profil_affiche_les_informations_de_l_utilisateur(client, utilisateur):
    client.force_login(utilisateur)

    reponse = client.get(reverse("comptes:profil"))
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert "secretaire1" in contenu
    assert "Marie Kalonji" in contenu


def test_modifier_profil_met_a_jour_les_champs(client, utilisateur):
    client.force_login(utilisateur)

    reponse = client.post(
        reverse("comptes:profil_modifier"),
        {"first_name": "Marie-Claire", "last_name": "Kalonji", "email": "marie@example.com"},
    )

    utilisateur.refresh_from_db()
    assert reponse.status_code == 302
    assert utilisateur.first_name == "Marie-Claire"
    assert utilisateur.email == "marie@example.com"


def test_changement_de_mot_de_passe(client, utilisateur):
    client.force_login(utilisateur)

    reponse = client.post(
        reverse("comptes:mot_de_passe_modifier"),
        {
            "old_password": "mot-de-passe-test-123",
            "new_password1": "un-nouveau-mot-de-passe-robuste",
            "new_password2": "un-nouveau-mot-de-passe-robuste",
        },
    )

    assert reponse.status_code == 302
    utilisateur.refresh_from_db()
    assert utilisateur.check_password("un-nouveau-mot-de-passe-robuste")


def test_profil_exige_authentification(client):
    reponse = client.get(reverse("comptes:profil"))

    assert reponse.status_code == 302
    assert reverse("comptes:connexion") in reponse.url
