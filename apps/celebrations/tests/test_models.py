import datetime

import pytest

from apps.comptes.models import Paroisse
from apps.celebrations.models import Celebration, IntentionMesse

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def test_creation_celebration(paroisse):
    celebration = Celebration.objects.create(
        date=datetime.date(2026, 8, 15),
        heure=datetime.time(9, 0),
        type_celebration="messe",
        celebrant="Abbé Kalonji",
        paroisse=paroisse,
    )

    assert celebration.pk is not None
    assert "Messe" in str(celebration)


def test_creation_intention_rattachee_a_une_celebration(paroisse):
    celebration = Celebration.objects.create(
        date=datetime.date(2026, 8, 15),
        heure=datetime.time(9, 0),
        type_celebration="messe",
        celebrant="Abbé Kalonji",
        paroisse=paroisse,
    )
    intention = IntentionMesse.objects.create(
        demandeur="Famille Mbala",
        intention="Action de grâce",
        montant_offrande=10,
        celebration=celebration,
        paroisse=paroisse,
    )

    assert intention.celebration == celebration
    assert intention.statut == "en_attente"
    assert intention in celebration.intentions.all()
