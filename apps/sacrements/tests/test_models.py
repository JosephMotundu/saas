import datetime

import pytest

from apps.comptes.models import Paroisse
from apps.paroissiens.models import Paroissien
from apps.sacrements.models import Bapteme, Mariage, MentionMarginale

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


@pytest.fixture
def paroissien(paroisse):
    return Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)


def test_numero_acte_genere_automatiquement(paroisse, paroissien):
    bapteme = Bapteme.objects.create(
        paroissien=paroissien,
        date=datetime.date(2026, 1, 12),
        celebrant="Abbé Kalonji",
        paroisse=paroisse,
    )

    assert bapteme.numero_acte == "BAP-2026-0001"


def test_numero_acte_incremente_par_annee_et_par_paroisse(paroisse, paroissien):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    autre_paroissien = Paroissien.objects.create(
        nom="Kalonji", prenom="Marie", sexe="F", paroisse=autre_paroisse
    )

    b1 = Bapteme.objects.create(
        paroissien=paroissien, date=datetime.date(2026, 1, 12), celebrant="Abbé K.", paroisse=paroisse
    )
    b2 = Bapteme.objects.create(
        paroissien=paroissien, date=datetime.date(2026, 2, 3), celebrant="Abbé K.", paroisse=paroisse
    )
    b3 = Bapteme.objects.create(
        paroissien=autre_paroissien,
        date=datetime.date(2026, 1, 20),
        celebrant="Abbé L.",
        paroisse=autre_paroisse,
    )

    assert b1.numero_acte == "BAP-2026-0001"
    assert b2.numero_acte == "BAP-2026-0002"
    assert b3.numero_acte == "BAP-2026-0001"  # compteur indépendant par paroisse


def test_mariage_relie_deux_paroissiens_distincts(paroisse):
    epoux = Paroissien.objects.create(nom="Mbala", prenom="Jean", sexe="M", paroisse=paroisse)
    epouse = Paroissien.objects.create(nom="Kalonji", prenom="Marie", sexe="F", paroisse=paroisse)

    mariage = Mariage.objects.create(
        conjoint1=epoux,
        conjoint2=epouse,
        date=datetime.date(2026, 6, 1),
        celebrant="Abbé Kalonji",
        paroisse=paroisse,
    )

    assert mariage.numero_acte == "MAR-2026-0001"
    assert mariage.conjoint1 == epoux
    assert mariage.conjoint2 == epouse


def test_mention_marginale_rattachee_a_un_bapteme(paroisse, paroissien):
    bapteme = Bapteme.objects.create(
        paroissien=paroissien, date=datetime.date(2000, 1, 1), celebrant="Abbé K.", paroisse=paroisse
    )

    mention = MentionMarginale.objects.create(
        bapteme=bapteme,
        type_mention="mariage",
        date=datetime.date(2026, 6, 1),
        reference="MAR-2026-0001",
        paroisse=paroisse,
    )

    assert mention in bapteme.mentions_marginales.all()
    assert str(mention) == f"Mariage — {bapteme}"
