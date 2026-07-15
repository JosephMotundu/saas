from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class SuperuserRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Réservé au superadmin de l'instance — contrairement à
    apps.comptes.mixins.RoleRequisMixin, aucun rôle de paroisse (Curé...)
    ne donne accès ici : la plateforme supervise toutes les paroisses,
    un Curé n'en gère qu'une."""

    def test_func(self):
        return self.request.user.is_superuser
