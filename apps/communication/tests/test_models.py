import datetime

import pytest

from apps.comptes.models import Paroisse, Utilisateur
from apps.communication.models import Annonce

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def test_creation_annonce(paroisse):
    auteur = Utilisateur.objects.create_user(
        username="secretaire1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    annonce = Annonce.objects.create(
        titre="Kermesse paroissiale",
        contenu="La kermesse aura lieu le mois prochain.",
        date_publication=datetime.date(2026, 7, 1),
        auteur=auteur,
        paroisse=paroisse,
    )

    assert annonce.pk is not None
    assert str(annonce) == "Kermesse paroissiale"
    assert annonce.groupe_cible is None
