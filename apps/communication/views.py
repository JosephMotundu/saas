from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.comptes.mixins import FiltrageParoisseMixin, RoleRequisMixin

from .forms import AnnonceForm
from .models import Annonce

ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)


class AnnonceListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Annonce
    template_name = "communication/annonce_liste.html"
    context_object_name = "annonces"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("auteur", "groupe_cible")


class AnnonceDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Annonce
    template_name = "communication/annonce_detail.html"
    context_object_name = "annonce"
    roles_autorises = ROLES_LECTURE


class AnnonceCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = Annonce
    form_class = AnnonceForm
    template_name = "communication/annonce_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        form.instance.auteur = self.request.user
        messages.success(self.request, "Annonce publiée.")
        return super().form_valid(form)


class AnnonceUpdateView(RoleRequisMixin, FiltrageParoisseMixin, UpdateView):
    model = Annonce
    form_class = AnnonceForm
    template_name = "communication/annonce_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class AnnonceDeleteView(RoleRequisMixin, FiltrageParoisseMixin, DeleteView):
    model = Annonce
    template_name = "communication/annonce_confirmer_suppression.html"
    success_url = reverse_lazy("communication:annonce_liste")
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Annonce supprimée.")
        return super().form_valid(form)
