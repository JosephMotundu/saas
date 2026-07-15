import pytest
from django.urls import reverse

from apps.comptes.models import Abonnement, Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


def _donnees_valides(**overrides):
    donnees = {
        "nom_paroisse": "Saint Raphaël",
        "diocese": "Kinshasa",
        "ville": "Kinshasa",
        "commune": "Gombe",
        "quartier": "Golf",
        "avenue": "12 avenue de la Cathédrale",
        "offre": "standard",
        "prenom": "Jean",
        "nom": "Mbala",
        "email": "cure@saintraphael.example",
        "nom_utilisateur": "cure_mbala",
        "mot_de_passe": "un-mot-de-passe-suffisamment-robuste",
        "mot_de_passe_confirmation": "un-mot-de-passe-suffisamment-robuste",
    }
    donnees.update(overrides)
    return donnees


def test_inscription_cree_paroisse_abonnement_et_compte_cure(client):
    reponse = client.post(reverse("core:souscription"), _donnees_valides())

    assert reponse.status_code == 302
    assert reponse.url == reverse("core:tableau_de_bord")

    paroisse = Paroisse.objects.get(nom="Saint Raphaël")
    assert paroisse.diocese == "Kinshasa"
    assert paroisse.commune == "Gombe"
    assert paroisse.quartier == "Golf"
    assert paroisse.avenue == "12 avenue de la Cathédrale"
    assert paroisse.adresse == "12 avenue de la Cathédrale, Golf, Gombe"

    abonnement = Abonnement.objects.get(paroisse=paroisse)
    assert abonnement.offre == "standard"
    assert abonnement.statut == "actif"

    assert paroisse.latitude is None
    assert paroisse.longitude is None

    cure = Utilisateur.objects.get(username="cure_mbala")
    assert cure.paroisse == paroisse
    assert cure.groups.filter(name="Curé").exists()
    assert cure.check_password("un-mot-de-passe-suffisamment-robuste")


def test_inscription_connecte_automatiquement_le_nouvel_utilisateur(client):
    client.post(reverse("core:souscription"), _donnees_valides())

    reponse = client.get(reverse("core:tableau_de_bord"))

    assert reponse.status_code == 200
    assert "Saint Raphaël" in reponse.content.decode()


def test_inscription_refuse_un_nom_de_paroisse_deja_pris(client):
    Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )

    reponse = client.post(reverse("core:souscription"), _donnees_valides())

    assert reponse.status_code == 200
    assert "porte déjà ce nom" in reponse.content.decode()


def test_inscription_refuse_un_nom_d_utilisateur_deja_pris(client):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    Utilisateur.objects.create_user(
        username="cure_mbala", password="autre-mot-de-passe-123", paroisse=autre_paroisse
    )

    reponse = client.post(reverse("core:souscription"), _donnees_valides())

    assert reponse.status_code == 200
    assert "déjà pris" in reponse.content.decode()
    assert not Paroisse.objects.filter(nom="Saint Raphaël").exists()


def test_inscription_refuse_des_mots_de_passe_differents(client):
    reponse = client.post(
        reverse("core:souscription"),
        _donnees_valides(mot_de_passe_confirmation="autre-chose"),
    )

    assert reponse.status_code == 200
    assert "ne correspondent pas" in reponse.content.decode()
    assert not Paroisse.objects.filter(nom="Saint Raphaël").exists()


def test_inscription_refuse_un_mot_de_passe_trop_simple(client):
    reponse = client.post(
        reverse("core:souscription"),
        _donnees_valides(mot_de_passe="12345678", mot_de_passe_confirmation="12345678"),
    )

    assert reponse.status_code == 200
    assert not Paroisse.objects.filter(nom="Saint Raphaël").exists()


def test_inscription_enregistre_les_coordonnees_pointees_sur_la_carte(client):
    client.post(
        reverse("core:souscription"),
        _donnees_valides(latitude="-4.305737", longitude="15.302001"),
    )

    paroisse = Paroisse.objects.get(nom="Saint Raphaël")

    assert str(paroisse.latitude) == "-4.305737"
    assert str(paroisse.longitude) == "15.302001"


def test_inscription_sans_quartier_compose_l_adresse_sans_lui(client):
    client.post(reverse("core:souscription"), _donnees_valides(quartier=""))

    paroisse = Paroisse.objects.get(nom="Saint Raphaël")

    assert paroisse.quartier == ""
    assert paroisse.adresse == "12 avenue de la Cathédrale, Gombe"
