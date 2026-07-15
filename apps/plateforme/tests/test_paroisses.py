import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Abonnement, Paroisse, Utilisateur
from apps.paroissiens.models import Paroissien

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    Abonnement.objects.create(paroisse=paroisse, offre="standard")
    return paroisse


@pytest.fixture
def superadmin():
    return Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )


def creer_cure(paroisse, username="cure1"):
    cure = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    cure.groups.add(Group.objects.get(name="Curé"))
    return cure


def test_seul_le_superadmin_accede_a_la_liste(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.get(reverse("plateforme:paroisse_liste"))

    assert reponse.status_code == 403


def test_la_liste_montre_toutes_les_paroisses_avec_leurs_stats(client, paroisse, superadmin):
    Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)
    client.force_login(superadmin)

    reponse = client.get(reverse("plateforme:paroisse_liste"))
    paroisse_annotee = reponse.context["paroisses"].get(pk=paroisse.pk)

    assert reponse.status_code == 200
    assert "Saint Raphaël" in reponse.content.decode()
    assert paroisse_annotee.nombre_paroissiens == 1


def test_suspendre_puis_reactiver_une_paroisse(client, paroisse, superadmin):
    client.force_login(superadmin)

    client.post(reverse("plateforme:paroisse_basculer_active", args=[paroisse.pk]))
    paroisse.refresh_from_db()
    assert paroisse.est_active is False

    client.post(reverse("plateforme:paroisse_basculer_active", args=[paroisse.pk]))
    paroisse.refresh_from_db()
    assert paroisse.est_active is True


def test_reinitialiser_le_mot_de_passe_d_un_membre(client, paroisse, superadmin):
    cure = creer_cure(paroisse)
    client.force_login(superadmin)

    reponse = client.post(
        reverse("plateforme:membre_reinitialiser_mot_de_passe", args=[cure.pk])
    )
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert "Mot de passe temporaire" in contenu

    cure.refresh_from_db()
    assert not cure.check_password("mot-de-passe-test-123")


def test_fiche_paroisse_liste_ses_membres(client, paroisse, superadmin):
    cure = creer_cure(paroisse)
    client.force_login(superadmin)

    reponse = client.get(reverse("plateforme:paroisse_detail", args=[paroisse.pk]))
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert cure.username in contenu
