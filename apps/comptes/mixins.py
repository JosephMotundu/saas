from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class FiltrageParoisseMixin(LoginRequiredMixin):
    """Isole les données par paroisse au niveau de la vue.

    Le manager par défaut de chaque modèle métier (apps.comptes.managers)
    filtre déjà automatiquement sur la paroisse courante — posée par
    ParoisseCouranteMiddleware sur `request.paroisse`. Ce mixin ajoute un
    filtrage explicite, redondant par construction : une défense en
    profondeur, pas le seul rempart. Il reste aussi responsable de
    rattacher tout objet créé à la paroisse courante.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(paroisse=self.request.paroisse)

    def form_valid(self, form):
        form.instance.paroisse = self.request.paroisse
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


class ExigeParoisseMixin:
    """Empêche un superadmin (paroisse=None) d'atteindre une vue qui
    suppose une paroisse courante (abonnement, équipe...). À combiner avec
    RoleRequisMixin ou FiltrageParoisseMixin, qui garantissent déjà
    l'authentification."""

    def dispatch(self, request, *args, **kwargs):
        if request.paroisse is None:
            messages.error(request, "Cette page suppose un compte rattaché à une paroisse.")
            return redirect("core:tableau_de_bord")
        return super().dispatch(request, *args, **kwargs)
