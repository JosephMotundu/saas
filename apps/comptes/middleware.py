from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

from .contexte import definir_paroisse_courante, reinitialiser_paroisse_courante


class ParoisseCouranteMiddleware:
    """Détermine la paroisse courante à partir de l'utilisateur connecté et
    l'expose sur `request.paroisse` (§4 du brief).

    Alimente aussi la ContextVar lue par les managers multi-tenant
    (apps.comptes.managers), afin que le filtrage par paroisse soit
    automatique même pour du code qui n'a pas accès à `request` (Django
    Admin, requêtes déclenchées en cascade lors du rendu d'un template...).

    Coupe aussi immédiatement l'accès d'une session déjà ouverte si la
    paroisse est suspendue entre-temps par la plateforme (le blocage à la
    connexion elle-même est géré séparément par ConnexionForm) — sans quoi
    une suspension n'aurait d'effet qu'à la prochaine reconnexion.

    Doit être placé après AuthenticationMiddleware dans MIDDLEWARE, puisqu'il
    dépend de request.user.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = getattr(request, "user", None)
        paroisse = None
        if utilisateur is not None and utilisateur.is_authenticated:
            paroisse = getattr(utilisateur, "paroisse", None)

            if paroisse is not None and not paroisse.est_active:
                chemins_autorises = {
                    reverse("comptes:connexion"),
                    reverse("comptes:deconnexion"),
                }
                if request.path not in chemins_autorises:
                    logout(request)
                    messages.error(
                        request,
                        "Votre paroisse a été suspendue. Contactez l'administrateur "
                        "de la plateforme.",
                    )
                    return redirect("comptes:connexion")
                paroisse = None

        request.paroisse = paroisse
        jeton = definir_paroisse_courante(paroisse)
        try:
            response = self.get_response(request)
        finally:
            reinitialiser_paroisse_courante(jeton)
        return response
