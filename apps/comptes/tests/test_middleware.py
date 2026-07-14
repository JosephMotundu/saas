import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from apps.comptes.contexte import obtenir_paroisse_courante
from apps.comptes.middleware import ParoisseCouranteMiddleware
from apps.comptes.models import Paroisse, Utilisateur

pytestmark = pytest.mark.django_db


@pytest.fixture
def paroisse():
    return Paroisse.objects.create(
        nom="Saint Raphaël", diocese="Kinshasa", adresse="12 avenue", ville="Kinshasa"
    )


def _appeler_middleware(request):
    paroisse_pendant_la_requete = {}

    def get_response(req):
        paroisse_pendant_la_requete["valeur"] = obtenir_paroisse_courante()
        return HttpResponse()

    middleware = ParoisseCouranteMiddleware(get_response)
    middleware(request)
    return paroisse_pendant_la_requete["valeur"]


def test_middleware_expose_la_paroisse_de_l_utilisateur_connecte(paroisse):
    utilisateur = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    request = RequestFactory().get("/")
    request.user = utilisateur

    valeur_pendant_la_requete = _appeler_middleware(request)

    assert request.paroisse == paroisse
    assert valeur_pendant_la_requete == paroisse


def test_middleware_ne_definit_rien_pour_le_superadmin():
    superadmin = Utilisateur.objects.create_superuser(
        username="admin", password="mot-de-passe-test-123", email="admin@example.com"
    )
    request = RequestFactory().get("/")
    request.user = superadmin

    valeur_pendant_la_requete = _appeler_middleware(request)

    assert request.paroisse is None
    assert valeur_pendant_la_requete is None


def test_middleware_ne_definit_rien_pour_un_utilisateur_anonyme():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    valeur_pendant_la_requete = _appeler_middleware(request)

    assert request.paroisse is None
    assert valeur_pendant_la_requete is None


def test_contextvar_reinitialisee_apres_la_requete(paroisse):
    utilisateur = Utilisateur.objects.create_user(
        username="cure1", password="mot-de-passe-test-123", paroisse=paroisse
    )
    request = RequestFactory().get("/")
    request.user = utilisateur

    _appeler_middleware(request)

    assert obtenir_paroisse_courante() is None
