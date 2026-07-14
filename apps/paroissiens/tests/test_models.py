import pytest

from apps.comptes.models import Paroisse
from apps.paroissiens.models import Famille, Paroissien

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def test_creation_famille(paroisse):
    famille = Famille.objects.create(nom="Mbala", paroisse=paroisse)

    assert famille.pk is not None
    assert str(famille) == "Mbala"


def test_creation_paroissien_rattache_a_une_famille(paroisse):
    famille = Famille.objects.create(nom="Mbala", paroisse=paroisse)
    paroissien = Paroissien.objects.create(
        nom="Mbala", prenom="Jean", sexe="M", famille=famille, paroisse=paroisse
    )

    assert paroissien.famille == famille
    assert paroissien.nom_complet() == "Jean Mbala"
    assert str(paroissien) == "Jean Mbala"


def test_suppression_famille_detache_les_paroissiens_sans_les_supprimer(paroisse):
    famille = Famille.objects.create(nom="Mbala", paroisse=paroisse)
    paroissien = Paroissien.objects.create(
        nom="Mbala", prenom="Jean", sexe="M", famille=famille, paroisse=paroisse
    )

    famille.delete()
    paroissien.refresh_from_db()

    assert paroissien.famille is None
