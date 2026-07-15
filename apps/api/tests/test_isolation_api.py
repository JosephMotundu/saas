import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APIClient

from apps.comptes.models import Paroisse, Utilisateur
from apps.paroissiens.models import Paroissien

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


@pytest.fixture
def autre_paroisse():
    return Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue de la Mission", ville="Kinshasa"
    )


def test_la_liste_api_ne_montre_que_la_paroisse_courante(paroisse, autre_paroisse):
    Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)
    Paroissien.objects.create(nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse)

    secretaire = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    secretaire.groups.add(Group.objects.get(name="Secrétaire"))
    client = APIClient()
    client.force_authenticate(user=secretaire)

    reponse = client.get(reverse("api:paroissien-list"))
    noms = {p["nom"] for p in reponse.data["results"]}

    assert noms == {"Mbala"}


def test_le_detail_d_un_autre_tenant_est_introuvable(paroisse, autre_paroisse):
    paroissien_autre = Paroissien.objects.create(
        nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse
    )
    secretaire = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    secretaire.groups.add(Group.objects.get(name="Secrétaire"))
    client = APIClient()
    client.force_authenticate(user=secretaire)

    reponse = client.get(reverse("api:paroissien-detail", args=[paroissien_autre.pk]))

    assert reponse.status_code == 404


def test_superadmin_sans_paroisse_ne_peut_pas_creer_de_paroissien(paroisse):
    superadmin = Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )
    client = APIClient()
    client.force_authenticate(user=superadmin)

    reponse = client.post(
        reverse("api:paroissien-list"), {"nom": "Mbala", "prenom": "Jean", "sexe": "M"}
    )

    assert reponse.status_code == 403
