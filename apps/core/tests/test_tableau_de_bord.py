import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël",
        diocese="Kinshasa",
        adresse="12 avenue de la Cathédrale",
        ville="Kinshasa",
    )


def test_tableau_de_bord_affiche_le_nombre_d_utilisateurs(client, paroisse):
    Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur = Utilisateur.objects.create_user(
        username="secretaire2", password="mot-de-passe-test-123", paroisse=paroisse
    )
    client.force_login(utilisateur)

    reponse = client.get(reverse("core:tableau_de_bord"))
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert "Saint Raphaël" in contenu
    assert ">2<" in contenu


def test_tableau_de_bord_sans_localisation_affiche_un_avis(client, paroisse):
    utilisateur = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    client.force_login(utilisateur)

    reponse = client.get(reverse("core:tableau_de_bord"))

    assert "Localisation non renseignée" in reponse.content.decode()
    assert 'id="carte-paroisse"' not in reponse.content.decode()


def test_tableau_de_bord_avec_localisation_affiche_la_carte(client, paroisse):
    paroisse.latitude = -4.325
    paroisse.longitude = 15.322
    paroisse.save()
    utilisateur = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    client.force_login(utilisateur)

    reponse = client.get(reverse("core:tableau_de_bord"))

    assert 'id="carte-paroisse"' in reponse.content.decode()


def test_navigation_du_cure_affiche_toutes_les_sections(client, paroisse):
    groupe = Group.objects.get(name="Curé")
    utilisateur = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur.groups.add(groupe)
    client.force_login(utilisateur)

    contenu = client.get(reverse("core:tableau_de_bord")).content.decode()

    for section in ["Paroissiens", "Sacrements", "Célébrations", "Finances", "Communication"]:
        assert section in contenu


def test_navigation_du_tresorier_limitee_aux_finances(client, paroisse):
    groupe = Group.objects.get(name="Trésorier")
    utilisateur = Utilisateur.objects.create_user(
        username="tresorier1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    utilisateur.groups.add(groupe)
    client.force_login(utilisateur)

    contenu = client.get(reverse("core:tableau_de_bord")).content.decode()

    assert "Finances" in contenu
    assert "Paroissiens" not in contenu
    assert "Sacrements" not in contenu
