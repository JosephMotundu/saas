from rest_framework.exceptions import PermissionDenied


class IsolationParoisseMixin:
    """Isolation multi-tenant pour les ViewSets DRF.

    Le manager par défaut des modèles (apps.comptes.managers) dépend d'une
    ContextVar positionnée par ParoisseCouranteMiddleware — un middleware
    Django classique, qui s'exécute AVANT que DRF authentifie la requête
    par JWT (l'authentification JWT n'a lieu que dans APIView.dispatch()).
    Pour une requête authentifiée uniquement par jeton (sans cookie de
    session), la ContextVar ne serait donc pas fiable. Ce mixin filtre par
    conséquent explicitement, sans dépendre du manager automatique.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.paroisse is None:
            return queryset.none()
        return queryset.filter(paroisse=self.request.user.paroisse)

    def exiger_paroisse(self):
        if self.request.user.paroisse is None:
            raise PermissionDenied(
                "Un superadministrateur ne peut pas créer de données "
                "rattachées à une paroisse via cette API."
            )
        return self.request.user.paroisse

    def perform_create(self, serializer):
        serializer.save(paroisse=self.exiger_paroisse())
