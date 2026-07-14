import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command

from apps.comptes.models import Abonnement, Paroisse, Utilisateur
from apps.paroissiens.models import Paroissien

pytestmark = pytest.mark.django_db


def test_seed_cree_la_paroisse_l_abonnement_et_un_compte_par_role():
    call_command("seed")

    paroisse = Paroisse.objects.get(nom="Saint Raphaël")
    assert Abonnement.objects.filter(paroisse=paroisse, statut="actif").exists()

    roles_attendus = {"Curé", "Secrétaire", "Trésorier", "Lecteur"}
    roles_obtenus = {
        groupe
        for utilisateur in Utilisateur.objects.filter(paroisse=paroisse)
        for groupe in utilisateur.groups.values_list("name", flat=True)
    }
    assert roles_attendus == roles_obtenus
    assert Utilisateur.objects.filter(username="admin", is_superuser=True).exists()


def test_seed_les_comptes_demo_peuvent_s_authentifier():
    call_command("seed")

    for username, mot_de_passe in [
        ("admin", "admin1234"),
        ("cure", "cure1234"),
        ("secretaire", "secretaire1234"),
        ("tresorier", "tresorier1234"),
        ("lecteur", "lecteur1234"),
    ]:
        assert authenticate(username=username, password=mot_de_passe) is not None


def test_seed_est_idempotent():
    call_command("seed")
    call_command("seed")

    assert Paroisse.objects.count() == 1
    assert Utilisateur.objects.count() == 5
    assert Paroissien.objects.count() == 1
