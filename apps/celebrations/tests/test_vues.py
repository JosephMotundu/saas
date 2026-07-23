import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur
from apps.celebrations.models import Celebration

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


def test_secretaire_peut_creer_une_celebration(client, paroisse):
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.post(
        reverse("celebrations:celebration_creer"),
        {
            "date": "2026-08-15",
            "heure": "09:00",
            "type_celebration": "messe",
            "celebrant": "Abbé Kalonji",
            "lieu": "Église Saint Raphaël",
        },
    )

    assert reponse.status_code == 302
    assert Celebration.objects.filter(paroisse=paroisse).exists()


def test_secretaire_peut_creer_une_intention(client, paroisse):
    celebration = Celebration.objects.create(
        date=datetime.date(2026, 8, 15),
        heure=datetime.time(9, 0),
        type_celebration="messe",
        celebrant="Abbé Kalonji",
        paroisse=paroisse,
    )
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.post(
        reverse("celebrations:intention_creer"),
        {
            "celebration": celebration.pk,
            "demandeur": "Famille Mbala",
            "intention": "Action de grâce",
            "montant_offrande": "10",
            "devise": "CDF",
            "statut": "en_attente",
        },
    )

    assert reponse.status_code == 302
    assert celebration.intentions.count() == 1


def test_lecteur_ne_peut_pas_creer_de_celebration(client, paroisse):
    lecteur = creer_utilisateur(paroisse, "Lecteur", "lecteur1")
    client.force_login(lecteur)

    reponse = client.get(reverse("celebrations:celebration_creer"))

    assert reponse.status_code == 403


def test_isolation_multi_tenant_sur_les_celebrations(client, paroisse):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    Celebration.objects.create(
        date=datetime.date(2026, 8, 15),
        heure=datetime.time(9, 0),
        type_celebration="messe",
        celebrant="Abbé Lumumba",
        paroisse=autre_paroisse,
    )
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.get(reverse("celebrations:celebration_liste"))

    assert "Lumumba" not in reponse.content.decode()
