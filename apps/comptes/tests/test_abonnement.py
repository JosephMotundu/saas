import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Abonnement, Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    Abonnement.objects.create(paroisse=paroisse, offre="standard")
    return paroisse


def creer_cure(paroisse, username="cure1"):
    cure = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    cure.groups.add(Group.objects.get(name="Curé"))
    return cure


def test_cure_peut_changer_d_offre(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.post(reverse("comptes:abonnement"), {"offre": "diocese"})

    assert reponse.status_code == 302
    paroisse.abonnement.refresh_from_db()
    assert paroisse.abonnement.offre == "diocese"


def test_cure_peut_annuler_puis_reactiver(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    client.post(reverse("comptes:abonnement_basculer_statut"))
    paroisse.abonnement.refresh_from_db()
    assert paroisse.abonnement.statut == "annule"
    assert paroisse.abonnement.date_annulation is not None

    client.post(reverse("comptes:abonnement_basculer_statut"))
    paroisse.abonnement.refresh_from_db()
    assert paroisse.abonnement.statut == "actif"
    assert paroisse.abonnement.date_annulation is None


def test_tresorier_ne_peut_pas_gerer_l_abonnement(client, paroisse):
    tresorier = Utilisateur.objects.create_user(
        username="tresorier1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    tresorier.groups.add(Group.objects.get(name="Trésorier"))
    client.force_login(tresorier)

    reponse = client.get(reverse("comptes:abonnement"))

    assert reponse.status_code == 403


def test_superadmin_sans_paroisse_redirige_proprement(client):
    superadmin = Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )
    client.force_login(superadmin)

    reponse = client.get(reverse("comptes:abonnement"))

    assert reponse.status_code == 302
    assert reponse.url == reverse("core:tableau_de_bord")
