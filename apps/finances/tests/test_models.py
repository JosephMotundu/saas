import datetime

import pytest

from apps.comptes.models import Paroisse
from apps.finances.models import Don, RecuFiscal
from apps.finances.services import enregistrer_don_avec_recu

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def test_don_anonyme_autorise(paroisse):
    don = Don.objects.create(
        montant=25,
        date=datetime.date(2026, 3, 1),
        type_don="offrande",
        mode_paiement="especes",
        paroisse=paroisse,
    )

    assert don.paroissien is None
    assert "Don anonyme" in str(don)


def test_service_enregistre_don_et_recu_dans_la_meme_transaction(paroisse):
    don, recu = enregistrer_don_avec_recu(
        paroisse=paroisse,
        montant=50,
        date=datetime.date(2026, 3, 1),
        type_don="dime",
        mode_paiement="mobile_money",
    )

    assert don.pk is not None
    assert recu.don == don
    assert recu.numero == "REC-2026-0001"


def test_echec_de_creation_du_recu_annule_le_don(paroisse, monkeypatch):
    """Si la création du reçu échoue, le don ne doit pas non plus être
    persisté : c'est tout l'intérêt de la transaction atomique."""

    def creation_qui_echoue(*args, **kwargs):
        raise RuntimeError("échec simulé de création du reçu")

    monkeypatch.setattr(RecuFiscal.objects, "create", creation_qui_echoue)

    with pytest.raises(RuntimeError):
        enregistrer_don_avec_recu(
            paroisse=paroisse,
            montant=50,
            date=datetime.date(2026, 3, 1),
            type_don="dime",
            mode_paiement="mobile_money",
        )

    assert Don.objects.count() == 0
