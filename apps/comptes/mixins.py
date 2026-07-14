from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class FiltrageParoisseMixin(LoginRequiredMixin):
    """Isole les données par paroisse tant que le manager/middleware
    multi-tenant (étape suivante du plan) n'existe pas encore.

    Filtre le queryset des vues de liste/détail sur la paroisse de
    l'utilisateur connecté, et rattache automatiquement tout objet créé à
    cette même paroisse.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(paroisse=self.request.user.paroisse)

    def form_valid(self, form):
        form.instance.paroisse = self.request.user.paroisse
        return super().form_valid(form)


class RoleRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restreint une vue aux membres des groupes listés dans `roles_autorises`.

    Le Curé (et le superadmin) a toujours accès, conformément au §7 du
    brief : « Curé : accès complet à sa paroisse. »
    """

    roles_autorises = ()

    def test_func(self):
        utilisateur = self.request.user
        if utilisateur.is_superuser:
            return True
        groupes = set(utilisateur.groups.values_list("name", flat=True))
        if "Curé" in groupes:
            return True
        return bool(groupes & set(self.roles_autorises))
