import datetime

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur
from apps.finances.models import Don
from apps.finances.services import enregistrer_don_avec_recu

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def creer_utilisateur(paroisse, nom_groupe, username):
    utilisateur = Utilisateur.objects.create_user(
        username=username, password="mot-de-passe-test-123", paroisse=paroisse
    )
    if nom_groupe:
        utilisateur.groups.add(Group.objects.get(name=nom_groupe))
    return utilisateur


def test_tresorier_peut_enregistrer_un_don_anonyme(client, paroisse):
    tresorier = creer_utilisateur(paroisse, "Trésorier", "tresorier1")
    client.force_login(tresorier)

    reponse = client.post(
        reverse("finances:don_creer"),
        {
            "montant": "25",
            "date": "2026-03-01",
            "type_don": "offrande",
            "mode_paiement": "especes",
        },
    )

    assert reponse.status_code == 302
    don = Don.objects.get(paroisse=paroisse)
    assert don.paroissien is None
    assert don.recu_fiscal.numero == "REC-2026-0001"


def test_secretaire_n_a_pas_acces_aux_dons(client, paroisse):
    secretaire = creer_utilisateur(paroisse, "Secrétaire", "secretaire1")
    client.force_login(secretaire)

    reponse = client.get(reverse("finances:don_liste"))

    assert reponse.status_code == 403


def test_recu_fiscal_imprimable(client, paroisse):
    don, recu = enregistrer_don_avec_recu(
        paroisse=paroisse, montant=25, date=datetime.date(2026, 3, 1), type_don="offrande", mode_paiement="especes"
    )
    lecteur = creer_utilisateur(paroisse, "Lecteur", "lecteur1")
    client.force_login(lecteur)

    reponse = client.get(reverse("finances:recu_fiscal", args=[don.pk]))
    contenu = reponse.content.decode()

    assert reponse.status_code == 200
    assert recu.numero in contenu


def test_isolation_multi_tenant_sur_les_dons(client, paroisse):
    autre_paroisse = Paroisse.objects.create(
        nom="Saint Pierre", diocese="Kinshasa", adresse="4 rue", ville="Kinshasa"
    )
    enregistrer_don_avec_recu(
        paroisse=autre_paroisse,
        montant=100,
        date=datetime.date(2026, 3, 1),
        type_don="dime",
        mode_paiement="virement",
    )
    tresorier = creer_utilisateur(paroisse, "Trésorier", "tresorier1")
    client.force_login(tresorier)

    reponse = client.get(reverse("finances:don_liste"))

    assert "100" not in reponse.content.decode()
