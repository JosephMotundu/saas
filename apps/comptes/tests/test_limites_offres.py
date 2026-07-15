import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Abonnement, Paroisse, Utilisateur
from apps.paroissiens.models import Paroissien

pytestmark = pytest.mark.django_db


def _creer_paroisse_avec_offre(offre, nom="Saint Raphaël"):
    paroisse = Paroisse.objects.create(
        nom=nom, diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    Abonnement.objects.create(paroisse=paroisse, offre=offre)
    return paroisse


def _creer_utilisateur(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    if nom_groupe:
        utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    return utilisateur


# ---------- Accès aux modules ----------


def test_essentiel_bloque_paroissiens_et_communication(client):
    paroisse = _creer_paroisse_avec_offre("essentiel")
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    assert client.get(reverse("paroissiens:paroissien_liste")).status_code == 302
    assert client.get(reverse("communication:annonce_liste")).status_code == 302


def test_essentiel_autorise_sacrements_celebrations_finances(client):
    paroisse = _creer_paroisse_avec_offre("essentiel")
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    assert client.get(reverse("sacrements:index")).status_code == 200
    assert client.get(reverse("celebrations:celebration_liste")).status_code == 200


def test_standard_autorise_paroissiens_mais_bloque_communication(client):
    paroisse = _creer_paroisse_avec_offre("standard")
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    assert client.get(reverse("paroissiens:paroissien_liste")).status_code == 200
    assert client.get(reverse("communication:annonce_liste")).status_code == 302


def test_diocese_autorise_tous_les_modules(client):
    paroisse = _creer_paroisse_avec_offre("diocese")
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    assert client.get(reverse("paroissiens:paroissien_liste")).status_code == 200
    assert client.get(reverse("communication:annonce_liste")).status_code == 200


def test_module_non_restreint_sans_abonnement(client):
    """Une paroisse sans Abonnement (cas de test / configuré hors flux
    normal) n'est jamais bloquée : la restriction est une règle de
    facturation, pas une isolation de sécurité."""
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    assert client.get(reverse("paroissiens:paroissien_liste")).status_code == 200
    assert client.get(reverse("communication:annonce_liste")).status_code == 200


def test_navigation_masque_les_modules_non_inclus(client):
    paroisse = _creer_paroisse_avec_offre("essentiel")
    cure = _creer_utilisateur(paroisse, "Curé", "cure1")
    client.force_login(cure)

    contenu = client.get(reverse("core:tableau_de_bord")).content.decode()

    assert "Sacrements" in contenu
    assert "Paroissiens" not in contenu
    assert "Communication" not in contenu


def test_page_publique_bloquee_si_offre_sans_communication(client):
    from apps.communication.models import Annonce

    paroisse = _creer_paroisse_avec_offre("standard")
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    Annonce.objects.create(
        titre="Test",
        contenu="...",
        date_publication="2026-08-01",
        auteur=secretaire,
        paroisse=paroisse,
        publique=True,
    )

    reponse = client.get(
        reverse("communication_publique:annonce_liste", kwargs={"slug": paroisse.slug})
    )

    assert reponse.status_code == 404


# ---------- Limites chiffrées ----------


def test_limite_utilisateurs_essentiel(client):
    paroisse = _creer_paroisse_avec_offre("essentiel")
    cure = _creer_utilisateur(paroisse, "Curé", "cure1")
    for i in range(3):
        _creer_utilisateur(paroisse, "Lecteur", f"lecteur{i}")
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_inviter"),
        {
            "prenom": "Nouveau",
            "nom": "Membre",
            "email": "nouveau@example.com",
            "nom_utilisateur": "nouveau_membre",
            "role": "Lecteur",
        },
    )

    assert reponse.status_code == 302
    assert not Utilisateur.objects.filter(username="nouveau_membre").exists()


def test_limite_utilisateurs_standard(client):
    paroisse = _creer_paroisse_avec_offre("standard")
    cure = _creer_utilisateur(paroisse, "Curé", "cure1")
    for i in range(7):
        _creer_utilisateur(paroisse, "Lecteur", f"lecteur{i}")
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_inviter"),
        {
            "prenom": "Nouveau",
            "nom": "Membre",
            "email": "nouveau@example.com",
            "nom_utilisateur": "nouveau_membre",
            "role": "Lecteur",
        },
    )

    assert reponse.status_code == 302
    assert not Utilisateur.objects.filter(username="nouveau_membre").exists()


def test_inviter_un_second_cure_ne_compte_pas_dans_la_limite(client):
    paroisse = _creer_paroisse_avec_offre("essentiel")
    cure = _creer_utilisateur(paroisse, "Curé", "cure1")
    for i in range(3):
        _creer_utilisateur(paroisse, "Lecteur", f"lecteur{i}")
    client.force_login(cure)

    reponse = client.post(
        reverse("comptes:equipe_inviter"),
        {
            "prenom": "Second",
            "nom": "Cure",
            "email": "second@example.com",
            "nom_utilisateur": "second_cure",
            "role": "Curé",
        },
    )

    assert reponse.status_code == 200
    assert Utilisateur.objects.filter(username="second_cure").exists()


def test_limite_paroissiens_standard(client):
    paroisse = _creer_paroisse_avec_offre("standard")
    secretaire = _creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    Paroissien.objects.bulk_create(
        [
            Paroissien(nom=f"Nom{i}", prenom="Test", sexe="M", paroisse=paroisse)
            for i in range(2000)
        ]
    )
    client.force_login(secretaire)

    reponse = client.post(
        reverse("paroissiens:paroissien_creer"),
        {"nom": "Le2001eme", "prenom": "Jean", "sexe": "M"},
    )

    assert reponse.status_code == 302
    assert not Paroissien.objects.filter(nom="Le2001eme").exists()
    assert Paroissien.objects.filter(paroisse=paroisse).count() == 2000
