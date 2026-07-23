import re

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


@pytest.fixture
def autre_paroisse():
    return Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )


def creer_cure(paroisse, username="cure1"):
    cure = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    cure.groups.add(Group.objects.get(name="Curé"))
    return cure


def test_cure_peut_inviter_un_collaborateur(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_inviter"),
        {
            "prenom": "Bernard",
            "nom": "Kanku",
            "email": "secretaire@saintraphael.example",
            "nom_utilisateur": "secretaire_kanku",
            "role": "Secrétaire",
        },
    )
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert "secretaire_kanku" in contenu
    assert "Mot de passe temporaire" in contenu

    membre = Utilisateur.objects.get(username="secretaire_kanku")
    assert membre.paroisse == paroisse
    assert membre.groups.filter(name="Secrétaire").exists()


def test_le_mot_de_passe_temporaire_affiche_permet_de_se_connecter(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_inviter"),
        {
            "prenom": "Bernard",
            "nom": "Kanku",
            "email": "secretaire@saintraphael.example",
            "nom_utilisateur": "secretaire_kanku",
            "role": "Secrétaire",
        },
    )
    mot_de_passe = re.search(
        r'<dd class="numerique">([^<]+)</dd>\s*</dl>', reponse.content.decode()
    ).group(1)

    client.logout()
    connecte = client.login(username="secretaire_kanku", password=mot_de_passe)

    assert connecte is True


def test_secretaire_ne_peut_pas_inviter(client, paroisse):
    secretaire = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    secretaire.groups.add(Group.objects.get(name="Secrétaire"))
    client.force_login(secretaire)

    reponse = client.get(reverse("comptes:equipe_inviter"))

    assert reponse.status_code == 403


def test_equipe_isolee_par_paroisse(client, paroisse, autre_paroisse):
    cure = creer_cure(paroisse)
    Utilisateur.objects.create_user(
        username="membre_autre", password="mot-de-passe-test-123", paroisse=autre_paroisse
    )
    client.force_login(cure)

    reponse = client.get(reverse("comptes:equipe"))
    contenu = reponse.content.decode()

    assert "cure1" in contenu
    assert "membre_autre" not in contenu


def test_cure_peut_desactiver_un_membre(client, paroisse):
    cure = creer_cure(paroisse)
    membre = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    client.force_login(cure)

    reponse = client.post(reverse("comptes:equipe_basculer_actif", args=[membre.pk]))

    assert reponse.status_code == 302
    membre.refresh_from_db()
    assert membre.is_active is False


def test_cure_ne_peut_pas_se_desactiver_lui_meme(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    client.post(reverse("comptes:equipe_basculer_actif", args=[cure.pk]))

    cure.refresh_from_db()
    assert cure.is_active is True


def test_cure_peut_modifier_un_membre_et_son_role(client, paroisse):
    cure = creer_cure(paroisse)
    membre = Utilisateur.objects.create_user(
        username="secretaire1",
        password="mot-de-passe-test-123",
        paroisse=paroisse,
        first_name="Ancien",
        last_name="Nom",
        email="ancien@example.com",
    )
    membre.groups.add(Group.objects.get(name="Secrétaire"))
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_modifier", args=[membre.pk]),
        {
            "prenom": "Nouveau",
            "nom": "Nom",
            "email": "nouveau@example.com",
            "role": "Trésorier",
        },
    )

    assert reponse.status_code == 302
    membre.refresh_from_db()
    assert membre.first_name == "Nouveau"
    assert membre.email == "nouveau@example.com"
    assert list(membre.groups.values_list("name", flat=True)) == ["Trésorier"]


def test_un_membre_ne_peut_pas_etre_promu_cure(client, paroisse):
    """Le Curé est unique par paroisse : on ne peut pas promouvoir un membre au
    rôle de Curé via la modification d'équipe. Le rôle du membre reste inchangé."""
    cure = creer_cure(paroisse)
    membre = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    membre.groups.add(Group.objects.get(name="Secrétaire"))
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_modifier", args=[membre.pk]),
        {
            "prenom": "Nouveau",
            "nom": "Nom",
            "email": "nouveau@example.com",
            "role": "Curé",
        },
    )

    assert reponse.status_code == 200  # formulaire ré-affiché avec l'erreur
    membre.refresh_from_db()
    assert list(membre.groups.values_list("name", flat=True)) == ["Secrétaire"]


def test_cure_ne_peut_pas_se_modifier_lui_meme_via_equipe(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.get(reverse("comptes:equipe_modifier", args=[cure.pk]))

    assert reponse.status_code == 302
    assert reponse.url == reverse("comptes:equipe")


def test_secretaire_ne_peut_pas_modifier_un_membre(client, paroisse):
    secretaire = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    secretaire.groups.add(Group.objects.get(name="Secrétaire"))
    autre = Utilisateur.objects.create_user(
        username="lecteur1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    client.force_login(secretaire)

    reponse = client.get(reverse("comptes:equipe_modifier", args=[autre.pk]))

    assert reponse.status_code == 403


def test_cure_ne_peut_pas_modifier_un_membre_dune_autre_paroisse(
    client, paroisse, autre_paroisse
):
    cure = creer_cure(paroisse)
    membre_autre = Utilisateur.objects.create_user(
        username="membre_autre", password="mot-de-passe-test-123", paroisse=autre_paroisse
    )
    client.force_login(cure)

    reponse = client.get(reverse("comptes:equipe_modifier", args=[membre_autre.pk]))

    assert reponse.status_code == 404


def test_cure_peut_reinitialiser_le_mot_de_passe_dun_membre(client, paroisse):
    cure = creer_cure(paroisse)
    membre = Utilisateur.objects.create_user(
        username="secretaire1", password="ancien-mot-de-passe", paroisse=paroisse
    )
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_reinitialiser_mot_de_passe", args=[membre.pk])
    )
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert "Mot de passe réinitialisé" in contenu

    mot_de_passe = re.search(
        r'<dd class="numerique">([^<]+)</dd>\s*</dl>', contenu
    ).group(1)

    client.logout()
    connecte = client.login(username="secretaire1", password=mot_de_passe)
    assert connecte is True


def test_cure_ne_peut_pas_reinitialiser_son_propre_mot_de_passe_via_equipe(client, paroisse):
    cure = creer_cure(paroisse)
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_reinitialiser_mot_de_passe", args=[cure.pk])
    )

    assert reponse.status_code == 302
    assert reponse.url == reverse("comptes:equipe")


def test_secretaire_ne_peut_pas_reinitialiser_un_mot_de_passe(client, paroisse):
    secretaire = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    secretaire.groups.add(Group.objects.get(name="Secrétaire"))
    autre = Utilisateur.objects.create_user(
        username="lecteur1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    client.force_login(secretaire)

    reponse = client.post(
        reverse("comptes:equipe_reinitialiser_mot_de_passe", args=[autre.pk])
    )

    assert reponse.status_code == 403
