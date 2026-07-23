import datetime

import pytest

from decimal import Decimal

from apps.celebrations.models import Celebration, IntentionMesse
from apps.comptes.models import Paroisse
from apps.finances.models import Depense, Don, OffrandeMesse, RecuFiscal
from apps.finances.services import (
    calculer_situation_financiere,
    enregistrer_don_avec_recu,
)

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


def test_solde_par_devise_est_recettes_moins_depenses(paroisse):
    Don.objects.create(
        montant=Decimal("100"),
        devise="USD",
        date=datetime.date(2026, 3, 1),
        type_don="dime",
        mode_paiement="especes",
        paroisse=paroisse,
    )
    Don.objects.create(
        montant=Decimal("50"),
        devise="USD",
        date=datetime.date(2026, 3, 2),
        type_don="offrande",
        mode_paiement="especes",
        paroisse=paroisse,
    )
    Depense.objects.create(
        libelle="Facture électricité",
        montant=Decimal("30"),
        devise="USD",
        date=datetime.date(2026, 3, 3),
        categorie="charges",
        mode_paiement="virement",
        paroisse=paroisse,
    )

    situation = calculer_situation_financiere(paroisse)
    usd = next(d for d in situation["par_devise"] if d["devise"] == "USD")

    assert usd["recettes"] == Decimal("150")
    assert usd["depenses"] == Decimal("30")
    assert usd["solde"] == Decimal("120")


def test_solde_agrege_dons_offrandes_messe_et_intentions(paroisse):
    """Les recettes cumulent trois sources : dons, offrandes de messe (quêtes)
    et offrandes des intentions (hors intentions annulées)."""
    Don.objects.create(
        montant=Decimal("100"), devise="USD", date=datetime.date(2026, 3, 1),
        type_don="dime", mode_paiement="especes", paroisse=paroisse,
    )
    OffrandeMesse.objects.create(
        montant=Decimal("40"), devise="USD", date=datetime.date(2026, 3, 2),
        mode_paiement="especes", paroisse=paroisse,
    )
    celebration = Celebration.objects.create(
        date=datetime.date(2026, 3, 3), heure=datetime.time(9, 0),
        type_celebration="messe", celebrant="Abbé Kalonji", paroisse=paroisse,
    )
    IntentionMesse.objects.create(
        demandeur="Famille Mbala", intention="Action de grâce",
        montant_offrande=Decimal("15"), devise="USD", statut="en_attente",
        celebration=celebration, paroisse=paroisse,
    )
    # Une intention annulée ne doit PAS compter dans les recettes.
    IntentionMesse.objects.create(
        demandeur="Anonyme", intention="Annulée",
        montant_offrande=Decimal("999"), devise="USD", statut="annulee",
        celebration=celebration, paroisse=paroisse,
    )

    situation = calculer_situation_financiere(paroisse)
    usd = next(d for d in situation["par_devise"] if d["devise"] == "USD")

    assert usd["dons"] == Decimal("100")
    assert usd["offrandes_messe"] == Decimal("40")
    assert usd["offrandes_intentions"] == Decimal("15")
    assert usd["recettes"] == Decimal("155")
    assert usd["solde"] == Decimal("155")


def test_dollars_et_francs_ne_sont_jamais_additionnes(paroisse):
    """Deux devises = deux soldes distincts, sans conversion (décision produit)."""
    Don.objects.create(
        montant=Decimal("100"),
        devise="USD",
        date=datetime.date(2026, 3, 1),
        type_don="dime",
        mode_paiement="especes",
        paroisse=paroisse,
    )
    Don.objects.create(
        montant=Decimal("30000"),
        devise="CDF",
        date=datetime.date(2026, 3, 2),
        type_don="offrande",
        mode_paiement="especes",
        paroisse=paroisse,
    )

    situation = calculer_situation_financiere(paroisse)
    par_devise = {d["devise"]: d for d in situation["par_devise"]}

    assert par_devise["USD"]["solde"] == Decimal("100")
    assert par_devise["CDF"]["solde"] == Decimal("30000")
    assert set(par_devise) == {"USD", "CDF"}


def test_situation_financiere_sans_mouvement_est_vide(paroisse):
    situation = calculer_situation_financiere(paroisse)

    assert situation["par_devise"] == []


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
