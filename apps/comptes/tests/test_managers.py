import datetime

import pytest

from apps.comptes.contexte import definir_paroisse_courante, reinitialiser_paroisse_courante
from apps.comptes.models import Paroisse
from apps.finances.services import enregistrer_don_avec_recu
from apps.finances.models import RecuFiscal
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


def test_manager_filtre_automatiquement_quand_la_paroisse_courante_est_definie(
    paroisse, autre_paroisse
):
    Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)
    Paroissien.objects.create(nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse)

    jeton = definir_paroisse_courante(paroisse)
    try:
        noms = set(Paroissien.objects.values_list("nom", flat=True))
    finally:
        reinitialiser_paroisse_courante(jeton)

    assert noms == {"Mbala"}


def test_manager_ne_filtre_rien_hors_contexte(paroisse, autre_paroisse):
    Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)
    Paroissien.objects.create(nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse)

    noms = set(Paroissien.objects.values_list("nom", flat=True))

    assert noms == {"Mbala", "Kalonji"}


def test_manager_filtre_via_une_relation_indirecte_recu_fiscal(paroisse, autre_paroisse):
    """RecuFiscal n'a pas de FK paroisse directe : le manager doit filtrer
    via don__paroisse."""
    _, recu_a = enregistrer_don_avec_recu(
        paroisse=paroisse,
        montant=10,
        date=datetime.date(2026, 1, 1),
        type_don="offrande",
        mode_paiement="especes",
    )
    enregistrer_don_avec_recu(
        paroisse=autre_paroisse,
        montant=20,
        date=datetime.date(2026, 1, 1),
        type_don="offrande",
        mode_paiement="especes",
    )

    jeton = definir_paroisse_courante(paroisse)
    try:
        numeros = set(RecuFiscal.objects.values_list("numero", flat=True))
    finally:
        reinitialiser_paroisse_courante(jeton)

    assert numeros == {recu_a.numero}
