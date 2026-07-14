import pytest

from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


def test_creation_paroisse():
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël",
        diocese="Kinshasa",
        adresse="12 avenue de la Cathédrale",
        ville="Kinshasa",
        telephone="+243 810 000 000",
        email="contact@saintraphael.example",
    )

    assert paroisse.pk is not None
    assert str(paroisse) == "Saint Raphaël"


def test_creation_utilisateur_rattache_a_une_paroisse():
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    utilisateur = Utilisateur.objects.create_user(
        username="secretaire1",
        password="mot-de-passe-test-123",
        paroisse=paroisse,
    )

    assert utilisateur.paroisse == paroisse
    assert utilisateur.check_password("mot-de-passe-test-123")
    assert utilisateur.password != "mot-de-passe-test-123"


def test_utilisateur_sans_paroisse_pour_superadmin():
    utilisateur = Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )

    assert utilisateur.paroisse is None
    assert utilisateur.is_superuser
