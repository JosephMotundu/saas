import pytest
from django.contrib.auth.models import Group

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("nom_groupe", ["Curé", "Secrétaire", "Trésorier", "Lecteur"])
def test_groupe_role_cree_par_la_migration(nom_groupe):
    assert Group.objects.filter(name=nom_groupe).exists()


def test_seuls_les_quatre_groupes_de_roles_existent():
    noms = set(Group.objects.values_list("name", flat=True))
    assert noms == {"Curé", "Secrétaire", "Trésorier", "Lecteur"}
