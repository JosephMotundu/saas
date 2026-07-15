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


def creer_client(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    if nom_groupe:
        utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    client = APIClient()
    client.force_authenticate(user=utilisateur)
    return client, utilisateur


def test_secretaire_peut_lister_et_creer_des_paroissiens(paroisse):
    client, _ = creer_client(paroisse, "Secrétaire", "secretaire1")

    reponse_creation = client.post(
        reverse("api:paroissien-list"), {"nom": "Mbala", "prenom": "Jean", "sexe": "M"}
    )
    reponse_liste = client.get(reverse("api:paroissien-list"))

    assert reponse_creation.status_code == 201
    assert reponse_liste.status_code == 200
    assert reponse_liste.data["count"] == 1

    paroissien = Paroissien.objects.get(nom="Mbala")
    assert paroissien.paroisse == paroisse


def test_lecteur_peut_lire_mais_pas_ecrire(paroisse):
    client, _ = creer_client(paroisse, "Lecteur", "lecteur1")

    reponse_lecture = client.get(reverse("api:paroissien-list"))
    reponse_ecriture = client.post(
        reverse("api:paroissien-list"), {"nom": "Mbala", "prenom": "Jean", "sexe": "M"}
    )

    assert reponse_lecture.status_code == 200
    assert reponse_ecriture.status_code == 403


def test_tresorier_n_a_pas_acces_aux_paroissiens(paroisse):
    client, _ = creer_client(paroisse, "Trésorier", "tresorier1")

    reponse = client.get(reverse("api:paroissien-list"))

    assert reponse.status_code == 403
