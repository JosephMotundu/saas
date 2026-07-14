from .contexte import definir_paroisse_courante, reinitialiser_paroisse_courante


class ParoisseCouranteMiddleware:
    """Détermine la paroisse courante à partir de l'utilisateur connecté et
    l'expose sur `request.paroisse` (§4 du brief).

    Alimente aussi la ContextVar lue par les managers multi-tenant
    (apps.comptes.managers), afin que le filtrage par paroisse soit
    automatique même pour du code qui n'a pas accès à `request` (Django
    Admin, requêtes déclenchées en cascade lors du rendu d'un template...).

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

        request.paroisse = paroisse
        jeton = definir_paroisse_courante(paroisse)
        try:
            response = self.get_response(request)
        finally:
            reinitialiser_paroisse_courante(jeton)
        return response
