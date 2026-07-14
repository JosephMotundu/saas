import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "nom_url",
    ["core:accueil", "core:fonctionnalites", "core:tarifs", "core:souscription"],
)
def test_page_publique_accessible(client, nom_url):
    reponse = client.get(reverse(nom_url))

    assert reponse.status_code == 200


def test_souscription_preselectionne_offre_depuis_la_query_string(client):
    reponse = client.get(reverse("core:souscription"), {"offre": "standard"})

    assert reponse.status_code == 200
    assert 'value="standard" selected' in reponse.content.decode()


def test_souscription_valide_affiche_une_confirmation_sans_persister(client):
    reponse = client.post(
        reverse("core:souscription"),
        {
            "nom_paroisse": "Saint Raphaël",
            "diocese": "Kinshasa",
            "ville": "Kinshasa",
            "email_contact": "contact@saintraphael.example",
            "offre": "standard",
        },
    )

    contenu = reponse.content.decode()
    assert reponse.status_code == 200
    assert "Merci, Saint Raphaël" in contenu
    assert "aucun paiement n'a été traité" in contenu


def test_tableau_de_bord_exige_authentification(client):
    reponse = client.get(reverse("core:tableau_de_bord"))

    assert reponse.status_code == 302
    assert reverse("comptes:connexion") in reponse.url
