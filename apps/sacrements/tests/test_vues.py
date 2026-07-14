import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur
from apps.paroissiens.models import Paroissien
from apps.sacrements.models import Bapteme

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


@pytest.fixture
def paroissien(paroisse):
    return Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)


def creer_utilisateur(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    if nom_groupe:
        utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    return utilisateur


def test_secretaire_peut_enregistrer_un_bapteme(client, paroisse, paroissien):
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.post(
        reverse("sacrements:bapteme_creer"),
        {
            "paroissien": paroissien.pk,
            "date": "2026-01-12",
            "lieu": "Église Saint Raphaël",
            "celebrant": "Abbé Kalonji",
            "parrain": "Pierre Tshisekedi",
            "marraine": "Anne Kabila",
        },
    )

    assert reponse.status_code == 302
    bapteme = Bapteme.objects.get(paroissien=paroissien)
    assert bapteme.numero_acte == "BAP-2026-0001"
    assert bapteme.paroisse == paroisse


def test_tresorier_n_a_pas_acces_au_registre_des_baptemes(client, paroisse):
    tresorier = creer_utilisateur(paroisse, "Trésorier", "tresorier1")
    client.force_login(tresorier)

    reponse = client.get(reverse("sacrements:bapteme_liste"))

    assert reponse.status_code == 403


def test_certificat_de_bapteme_accessible_en_lecture(client, paroisse, paroissien):
    lecteur = creer_utilisateur(paroisse, "Lecteur", "lecteur1")
    bapteme = Bapteme.objects.create(
        paroissien=paroissien, date=datetime.date(2026, 1, 12), celebrant="Abbé Kalonji", paroisse=paroisse
    )
    client.force_login(lecteur)

    reponse = client.get(reverse("sacrements:bapteme_certificat", args=[bapteme.pk]))
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert bapteme.numero_acte in contenu
    assert "Certificat" in contenu


def test_ajout_mention_marginale(client, paroisse, paroissien):
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    bapteme = Bapteme.objects.create(
        paroissien=paroissien, date=datetime.date(2000, 1, 1), celebrant="Abbé K.", paroisse=paroisse
    )
    client.force_login(secretaire)

    reponse = client.post(
        reverse("sacrements:mention_marginale_creer", args=[bapteme.pk]),
        {"type_mention": "mariage", "date": "2026-06-01", "reference": "MAR-2026-0001"},
    )

    assert reponse.status_code == 302
    assert bapteme.mentions_marginales.count() == 1


def test_isolation_multi_tenant_sur_le_registre_des_baptemes(client, paroisse):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    autre_paroissien = Paroissien.objects.create(
        nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse
    )
    Bapteme.objects.create(
        paroissien=autre_paroissien, date=datetime.date(2026, 1, 1), celebrant="Abbé L.", paroisse=autre_paroisse
    )

    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.get(reverse("sacrements:bapteme_liste"))

    assert "Kalonji" not in reponse.content.decode()
