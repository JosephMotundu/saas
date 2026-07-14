import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

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


def creer_utilisateur(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    if nom_groupe:
        utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    return utilisateur


def test_secretaire_peut_creer_un_paroissien(client, paroisse):
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.post(
        reverse("paroissiens:paroissien_creer"),
        {"nom": "Mbala", "prenom": "Jean", "sexe": "M"},
    )

    assert reponse.status_code == 302
    paroissien = Paroissien.objects.get(nom="Mbala")
    assert paroissien.paroisse == paroisse


def test_lecteur_ne_peut_pas_creer_un_paroissien(client, paroisse):
    lecteur = creer_utilisateur(paroisse, "Lecteur", "lecteur1")
    client.force_login(lecteur)

    reponse = client.get(reverse("paroissiens:paroissien_creer"))

    assert reponse.status_code == 403


def test_lecteur_peut_consulter_la_liste(client, paroisse):
    lecteur = creer_utilisateur(paroisse, "Lecteur", "lecteur1")
    client.force_login(lecteur)

    reponse = client.get(reverse("paroissiens:paroissien_liste"))

    assert reponse.status_code == 200


def test_tresorier_n_a_pas_acces_aux_paroissiens(client, paroisse):
    tresorier = creer_utilisateur(paroisse, "Trésorier", "tresorier1")
    client.force_login(tresorier)

    reponse = client.get(reverse("paroissiens:paroissien_liste"))

    assert reponse.status_code == 403


def test_isolation_multi_tenant_sur_la_liste(client, paroisse, autre_paroisse):
    Paroissien.objects.create(nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse)
    Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)

    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.get(reverse("paroissiens:paroissien_liste"))
    contenu = reponse.content.decode()

    assert "Mbala" in contenu
    assert "Kalonji" not in contenu


def test_isolation_multi_tenant_sur_le_detail(client, paroisse, autre_paroisse):
    paroissien_autre = Paroissien.objects.create(
        nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse
    )
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.get(
        reverse("paroissiens:paroissien_detail", args=[paroissien_autre.pk])
    )

    assert reponse.status_code == 404
