from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.comptes.mixins import FiltrageParoisseMixin, ModuleAutoriseMixin, RoleRequisMixin

from .forms import FamilleForm, ParoissienForm
from .models import Famille, Paroissien

ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)


class ParoissienListView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, ListView):
    model = Paroissien
    template_name = "paroissiens/paroissien_liste.html"
    context_object_name = "paroissiens"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE
    module_requis = "paroissiens"

    def get_queryset(self):
        return super().get_queryset().select_related("famille").order_by("nom", "prenom")


class ParoissienDetailView(
    RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, DetailView
):
    model = Paroissien
    template_name = "paroissiens/paroissien_detail.html"
    context_object_name = "paroissien"
    roles_autorises = ROLES_LECTURE
    module_requis = "paroissiens"


class ParoissienCreateView(
    RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, CreateView
):
    model = Paroissien
    form_class = ParoissienForm
    template_name = "paroissiens/paroissien_form.html"
    roles_autorises = ROLES_ECRITURE
    module_requis = "paroissiens"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        abonnement = getattr(self.request.paroisse, "abonnement", None)
        if abonnement is not None:
            limite = abonnement.max_paroissiens()
            if (
                limite is not None
                and Paroissien.objects.filter(paroisse=self.request.paroisse).count() >= limite
            ):
                messages.error(
                    self.request,
                    f"Votre offre {abonnement.get_offre_display()} est limitée à "
                    f"{limite} paroissiens. Passez à une offre supérieure pour en "
                    "ajouter davantage.",
                )
                return redirect("paroissiens:paroissien_liste")
        messages.success(self.request, "Paroissien enregistré.")
        return super().form_valid(form)


class ParoissienUpdateView(
    RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, UpdateView
):
    model = Paroissien
    form_class = ParoissienForm
    template_name = "paroissiens/paroissien_form.html"
    roles_autorises = ROLES_ECRITURE
    module_requis = "paroissiens"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class ParoissienDeleteView(
    RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, DeleteView
):
    model = Paroissien
    template_name = "paroissiens/paroissien_confirmer_suppression.html"
    success_url = reverse_lazy("paroissiens:paroissien_liste")
    roles_autorises = ROLES_ECRITURE
    module_requis = "paroissiens"

    def form_valid(self, form):
        messages.success(self.request, "Paroissien supprimé.")
        return super().form_valid(form)


class FamilleListView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, ListView):
    model = Famille
    template_name = "paroissiens/famille_liste.html"
    context_object_name = "familles"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE
    module_requis = "paroissiens"


class FamilleDetailView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, DetailView):
    model = Famille
    template_name = "paroissiens/famille_detail.html"
    context_object_name = "famille"
    roles_autorises = ROLES_LECTURE
    module_requis = "paroissiens"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("membres")


class FamilleCreateView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, CreateView):
    model = Famille
    form_class = FamilleForm
    template_name = "paroissiens/famille_form.html"
    roles_autorises = ROLES_ECRITURE
    module_requis = "paroissiens"

    def form_valid(self, form):
        messages.success(self.request, "Famille enregistrée.")
        return super().form_valid(form)


class FamilleUpdateView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, UpdateView):
    model = Famille
    form_class = FamilleForm
    template_name = "paroissiens/famille_form.html"
    roles_autorises = ROLES_ECRITURE
    module_requis = "paroissiens"

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class FamilleDeleteView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, DeleteView):
    model = Famille
    template_name = "paroissiens/famille_confirmer_suppression.html"
    success_url = reverse_lazy("paroissiens:famille_liste")
    roles_autorises = ROLES_ECRITURE
    module_requis = "paroissiens"

    def form_valid(self, form):
        messages.success(self.request, "Famille supprimée.")
        return super().form_valid(form)
