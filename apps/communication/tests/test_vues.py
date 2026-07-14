import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur
from apps.communication.models import Annonce

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def creer_utilisateur(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    if nom_groupe:
        utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    return utilisateur


def test_secretaire_peut_publier_une_annonce(client, paroisse):
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.post(
        reverse("communication:annonce_creer"),
        {
            "titre": "Kermesse paroissiale",
            "contenu": "La kermesse aura lieu le mois prochain.",
            "date_publication": "2026-07-01",
        },
    )

    assert reponse.status_code == 302
    annonce = Annonce.objects.get(titre="Kermesse paroissiale")
    assert annonce.auteur == secretaire
    assert annonce.paroisse == paroisse


def test_lecteur_ne_peut_pas_publier_une_annonce(client, paroisse):
    lecteur = creer_utilisateur(paroisse, "Lecteur", "lecteur1")
    client.force_login(lecteur)

    reponse = client.get(reverse("communication:annonce_creer"))

    assert reponse.status_code == 403


def test_isolation_multi_tenant_sur_les_annonces(client, paroisse):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    autre_auteur = Utilisateur.objects.create_user(
        username="secretaire2", password="mot-de-passe-test-123", paroisse=autre_paroisse
    )
    Annonce.objects.create(
        titre="Annonce d'une autre paroisse",
        contenu="...",
        date_publication="2026-07-01",
        auteur=autre_auteur,
        paroisse=autre_paroisse,
    )
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.get(reverse("communication:annonce_liste"))

    assert "Annonce d'une autre paroisse" not in reponse.content.decode()
