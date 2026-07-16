import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.celebrations.models import Celebration, IntentionMesse
from apps.comptes.models import Abonnement, Paroisse, Utilisateur
from apps.communication.models import Annonce
from apps.finances.models import Don, RecuFiscal
from apps.paroissiens.models import Famille, Paroissien
from apps.sacrements.models import Bapteme, Mariage

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


def peupler_paroisse(paroisse, cure):
    famille = Famille.objects.create(nom="Mbala", paroisse=paroisse)
    epoux = Paroissien.objects.create(
        nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse, famille=famille
    )
    epouse = Paroissien.objects.create(
        nom="Kanku", prenom="Marie", sexe="F", paroisse=paroisse
    )
    Bapteme.objects.create(
        date=datetime.date(2020, 1, 1),
        celebrant="Abbé X",
        paroissien=epoux,
        paroisse=paroisse,
    )
    Mariage.objects.create(
        date=datetime.date(2021, 1, 1),
        celebrant="Abbé X",
        conjoint1=epoux,
        conjoint2=epouse,
        paroisse=paroisse,
    )
    celebration = Celebration.objects.create(
        date=datetime.date(2026, 8, 1),
        heure="08:00",
        type_celebration="messe",
        celebrant="Abbé X",
        paroisse=paroisse,
    )
    IntentionMesse.objects.create(
        demandeur="Jean Mbala",
        intention="Action de grâce",
        celebration=celebration,
        paroisse=paroisse,
    )
    don = Don.objects.create(
        montant=50,
        date=datetime.date(2026, 1, 1),
        type_don="dime",
        mode_paiement="especes",
        paroissien=epoux,
        paroisse=paroisse,
    )
    RecuFiscal.objects.create(don=don)
    Annonce.objects.create(
        titre="Kermesse",
        contenu="...",
        date_publication=datetime.date(2026, 8, 1),
        auteur=cure,
        paroisse=paroisse,
    )


def test_seul_le_superadmin_peut_supprimer_une_paroisse(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.post(
        reverse("plateforme:paroisse_supprimer", args=[paroisse.pk]),
        {"confirmation": paroisse.nom},
    )

    assert reponse.status_code == 403
    assert Paroisse.objects.filter(pk=paroisse.pk).exists()


def test_supprimer_une_paroisse_efface_toutes_ses_donnees(client, paroisse, superadmin):
    cure = creer_cure(paroisse)
    peupler_paroisse(paroisse, cure)
    client.force_login(superadmin)

    reponse = client.post(
        reverse("plateforme:paroisse_supprimer", args=[paroisse.pk]),
        {"confirmation": paroisse.nom},
    )

    assert reponse.status_code == 302
    assert not Paroisse.objects.filter(pk=paroisse.pk).exists()
    assert not Utilisateur.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Paroissien.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Famille.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Bapteme.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Mariage.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Celebration.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not IntentionMesse.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Don.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not RecuFiscal.objects.exists()
    assert not Annonce.objects.filter(paroisse_id=paroisse.pk).exists()
    assert not Abonnement.objects.filter(paroisse_id=paroisse.pk).exists()


def test_supprimer_une_paroisse_exige_de_retaper_son_nom(client, paroisse, superadmin):
    cure = creer_cure(paroisse)
    client.force_login(superadmin)

    reponse = client.post(
        reverse("plateforme:paroisse_supprimer", args=[paroisse.pk]),
        {"confirmation": "Mauvais nom"},
    )

    assert reponse.status_code == 200
    assert Paroisse.objects.filter(pk=paroisse.pk).exists()
    assert Utilisateur.objects.filter(pk=cure.pk).exists()


def test_supprimer_une_paroisse_ne_touche_pas_les_autres(client, paroisse, superadmin):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    Abonnement.objects.create(paroisse=autre_paroisse, offre="standard")
    creer_cure(autre_paroisse, username="cure_autre")
    client.force_login(superadmin)

    client.post(
        reverse("plateforme:paroisse_supprimer", args=[paroisse.pk]),
        {"confirmation": paroisse.nom},
    )

    assert Paroisse.objects.filter(pk=autre_paroisse.pk).exists()
    assert Utilisateur.objects.filter(username="cure_autre").exists()
