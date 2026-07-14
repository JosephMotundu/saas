import pytest
from django.contrib.admin.sites import AdminSite

from apps.comptes.admin import ParoisseAdmin, UtilisateurAdmin
from apps.comptes.contexte import definir_paroisse_courante, reinitialiser_paroisse_courante
from apps.comptes.models import Paroisse, Utilisateur
from apps.paroissiens.admin import ParoissienAdmin
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


def test_admin_paroisse_isole_les_non_superusers(rf, paroisse, autre_paroisse):
    cure = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    request = rf.get("/admin/comptes/paroisse/")
    request.user = cure

    queryset = ParoisseAdmin(Paroisse, AdminSite()).get_queryset(request)

    assert list(queryset) == [paroisse]


def test_admin_paroisse_superuser_voit_toutes_les_paroisses(rf, paroisse, autre_paroisse):
    superadmin = Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )
    request = rf.get("/admin/comptes/paroisse/")
    request.user = superadmin

    queryset = ParoisseAdmin(Paroisse, AdminSite()).get_queryset(request)

    assert set(queryset) == {paroisse, autre_paroisse}


def test_admin_utilisateur_isole_les_non_superusers(rf, paroisse, autre_paroisse):
    cure = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    Utilisateur.objects.create_user(
        username="secretaire_autre", password="mot-de-passe-test-123", paroisse=autre_paroisse
    )
    request = rf.get("/admin/comptes/utilisateur/")
    request.user = cure

    queryset = UtilisateurAdmin(Utilisateur, AdminSite()).get_queryset(request)

    assert set(queryset.values_list("username", flat=True)) == {"cure1"}


def test_admin_paroissien_isole_automatiquement_via_le_manager(rf, paroisse, autre_paroisse):
    """Contrairement à ParoisseAdmin/UtilisateurAdmin, ParoissienAdmin ne
    définit aucun get_queryset() : l'isolation vient uniquement du manager
    par défaut du modèle, alimenté par la ContextVar que
    ParoisseCouranteMiddleware positionne à chaque requête (ici simulée
    directement, comme le ferait le middleware)."""
    Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)
    Paroissien.objects.create(nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse)
    cure = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    request = rf.get("/admin/paroissiens/paroissien/")
    request.user = cure

    jeton = definir_paroisse_courante(paroisse)
    try:
        queryset = ParoissienAdmin(Paroissien, AdminSite()).get_queryset(request)
        noms = list(queryset.values_list("nom", flat=True))
    finally:
        reinitialiser_paroisse_courante(jeton)

    assert noms == ["Mbala"]
