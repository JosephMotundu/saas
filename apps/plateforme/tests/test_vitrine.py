import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.comptes.models import Paroisse, Utilisateur
from apps.core.models import ContenuVitrine

pytestmark = pytest.mark.django_db


@pytest.fixture
def superadmin():
    return Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )


def test_contenu_vitrine_charger_cree_une_instance_par_defaut():
    contenu = ContenuVitrine.charger()

    assert contenu.pk is not None
    assert ContenuVitrine.objects.count() == 1
    assert ContenuVitrine.charger().pk == contenu.pk


def test_seul_le_superadmin_peut_modifier_la_vitrine(client):
    paroisse = Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )
    cure = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    cure.groups.add(Group.objects.get(name="Curé"))
    client.force_login(cure)

    reponse = client.get(reverse("plateforme:vitrine_modifier"))

    assert reponse.status_code == 403


def test_modifier_la_vitrine_se_repercute_sur_l_accueil(client, superadmin):
    client.force_login(superadmin)

    client.post(
        reverse("plateforme:vitrine_modifier"),
        {
            "titre_hero": "Titre personnalisé",
            "accroche_hero": "Une accroche personnalisée.",
            "titre_cta": "Rejoignez-nous",
            "texte_cta": "Un texte d'appel à l'action personnalisé.",
        },
    )

    reponse_accueil = client.get(reverse("core:accueil"))

    assert "Titre personnalisé" in reponse_accueil.content.decode()
