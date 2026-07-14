from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.comptes.mixins import FiltrageParoisseMixin, RoleRequisMixin

from .forms import FamilleForm, ParoissienForm
from .models import Famille, Paroissien

ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)


class ParoissienListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Paroissien
    template_name = "paroissiens/paroissien_liste.html"
    context_object_name = "paroissiens"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("famille").order_by("nom", "prenom")


class ParoissienDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Paroissien
    template_name = "paroissiens/paroissien_detail.html"
    context_object_name = "paroissien"
    roles_autorises = ROLES_LECTURE


class ParoissienCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = Paroissien
    form_class = ParoissienForm
    template_name = "paroissiens/paroissien_form.html"
    roles_autorises = ROLES_ECRITURE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Paroissien enregistré.")
        return super().form_valid(form)


class ParoissienUpdateView(RoleRequisMixin, FiltrageParoisseMixin, UpdateView):
    model = Paroissien
    form_class = ParoissienForm
    template_name = "paroissiens/paroissien_form.html"
    roles_autorises = ROLES_ECRITURE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class ParoissienDeleteView(RoleRequisMixin, FiltrageParoisseMixin, DeleteView):
    model = Paroissien
    template_name = "paroissiens/paroissien_confirmer_suppression.html"
    success_url = reverse_lazy("paroissiens:paroissien_liste")
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Paroissien supprimé.")
        return super().form_valid(form)


class FamilleListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Famille
    template_name = "paroissiens/famille_liste.html"
    context_object_name = "familles"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE


class FamilleDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Famille
    template_name = "paroissiens/famille_detail.html"
    context_object_name = "famille"
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().prefetch_related("membres")


class FamilleCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = Famille
    form_class = FamilleForm
    template_name = "paroissiens/famille_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Famille enregistrée.")
        return super().form_valid(form)


class FamilleUpdateView(RoleRequisMixin, FiltrageParoisseMixin, UpdateView):
    model = Famille
    form_class = FamilleForm
    template_name = "paroissiens/famille_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class FamilleDeleteView(RoleRequisMixin, FiltrageParoisseMixin, DeleteView):
    model = Famille
    template_name = "paroissiens/famille_confirmer_suppression.html"
    success_url = reverse_lazy("paroissiens:famille_liste")
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Famille supprimée.")
        return super().form_valid(form)
