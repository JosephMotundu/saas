from rest_framework.permissions import SAFE_METHODS, BasePermission


def creer_permission_role(roles_lecture=(), roles_ecriture=()):
    """Fabrique une classe de permission DRF équivalente à
    apps.comptes.mixins.RoleRequisMixin : le Curé (et le superuser) a
    toujours accès ; les autres rôles selon la méthode HTTP."""

    class PermissionRole(BasePermission):
        def has_permission(self, request, view):
            utilisateur = request.user
            if not utilisateur or not utilisateur.is_authenticated:
                return False
            if utilisateur.is_superuser:
                return True
            groupes = set(utilisateur.groups.values_list("name", flat=True))
            if "Curé" in groupes:
                return True
            roles_autorises = roles_lecture if request.method in SAFE_METHODS else roles_ecriture
            return bool(groupes & set(roles_autorises))

    return PermissionRole
