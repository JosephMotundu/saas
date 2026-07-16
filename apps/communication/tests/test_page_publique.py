import datetime

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


@pytest.fixture
def secretaire(paroisse):
    utilisateur = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur.groups.add(Group.objects.get(name="Secrétaire"))
    return utilisateur


def test_paroisse_recoit_un_slug_automatiquement(paroisse):
    assert paroisse.slug == "saint-raphael"


def test_deux_paroisses_de_nom_proche_ont_des_slugs_distincts():
    p1 = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="A", ville="Kinshasa"
    )
    p2 = Paroisse.objects.create(
        nom="Saint-Pierre", diocese="Kinshasa", adresse="B", ville="Kinshasa"
    )

    assert p1.slug != p2.slug


def test_page_publique_accessible_sans_authentification(client, paroisse, secretaire):
    Annonce.objects.create(
        titre="Kermesse annuelle",
        contenu="Ouverte à tous.",
        date_publication=datetime.date(2026, 8, 1),
        auteur=secretaire,
        paroisse=paroisse,
        publique=True,
    )

    reponse = client.get(
        reverse("communication_publique:annonce_liste", kwargs={"slug": paroisse.slug})
    )

    assert reponse.status_code == 200
    assert "Kermesse annuelle" in reponse.content.decode()


def test_page_publique_cache_les_annonces_non_publiques(client, paroisse, secretaire):
    Annonce.objects.create(
        titre="Réunion du conseil",
        contenu="Interne.",
        date_publication=datetime.date(2026, 8, 2),
        auteur=secretaire,
        paroisse=paroisse,
        publique=False,
    )

    reponse = client.get(
        reverse("communication_publique:annonce_liste", kwargs={"slug": paroisse.slug})
    )

    assert "Réunion du conseil" not in reponse.content.decode()


def test_annonce_non_publique_404_pour_un_invite(client, paroisse, secretaire):
    annonce = Annonce.objects.create(
        titre="Réunion du conseil",
        contenu="Interne.",
        date_publication=datetime.date(2026, 8, 2),
        auteur=secretaire,
        paroisse=paroisse,
        publique=False,
    )

    reponse = client.get(
        reverse(
            "communication_publique:annonce_detail",
            kwargs={"slug": paroisse.slug, "pk": annonce.pk},
        )
    )

    assert reponse.status_code == 404


def test_page_publique_404_si_paroisse_suspendue(client, paroisse, secretaire):
    Annonce.objects.create(
        titre="Kermesse annuelle",
        contenu="Ouverte à tous.",
        date_publication=datetime.date(2026, 8, 1),
        auteur=secretaire,
        paroisse=paroisse,
        publique=True,
    )
    paroisse.est_active = False
    paroisse.save()

    reponse = client.get(
        reverse("communication_publique:annonce_liste", kwargs={"slug": paroisse.slug})
    )

    assert reponse.status_code == 404


def test_page_publique_isolee_par_paroisse(client, paroisse, secretaire):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    Annonce.objects.create(
        titre="Annonce de Saint Pierre",
        contenu="...",
        date_publication=datetime.date(2026, 8, 1),
        auteur=secretaire,
        paroisse=autre_paroisse,
        publique=True,
    )

    reponse = client.get(
        reverse("communication_publique:annonce_liste", kwargs={"slug": paroisse.slug})
    )

    assert "Annonce de Saint Pierre" not in reponse.content.decode()


def test_pied_de_page_affiche_le_nom_de_la_paroisse_sur_la_page_publique(
    client, paroisse, secretaire
):
    reponse = client.get(
        reverse("communication_publique:annonce_liste", kwargs={"slug": paroisse.slug})
    )

    assert "Saint Raphaël" in reponse.content.decode()


def test_pied_de_page_ne_montre_aucune_paroisse_pour_un_visiteur_anonyme(client):
    reponse = client.get(reverse("core:accueil"))
    contenu = reponse.content.decode()

    assert "ParoisseConnect" in contenu
    assert "Saint Raphaël" not in contenu


def test_secretaire_peut_marquer_une_annonce_publique(client, paroisse, secretaire):
    client.force_login(secretaire)

    reponse = client.post(
        reverse("communication:annonce_creer"),
        {
            "titre": "Kermesse annuelle",
            "contenu": "Ouverte à tous.",
            "date_publication": "2026-08-01",
            "publique": "on",
        },
    )

    assert reponse.status_code == 302
    annonce = Annonce.objects.get(titre="Kermesse annuelle")
    assert annonce.publique is True
