from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.comptes.mixins import FiltrageParoisseMixin, ModuleAutoriseMixin, RoleRequisMixin
from apps.comptes.models import Paroisse

from .forms import AnnonceForm
from .models import Annonce

ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)


def _verifier_module_communication(paroisse):
    """Une paroisse dont l'offre n'inclut plus la communication perd aussi
    sa page publique — l'espace public est une conséquence du module, pas
    un droit acquis indépendant (cf. discussion tarifs)."""
    abonnement = getattr(paroisse, "abonnement", None)
    if abonnement is not None and not abonnement.module_autorise("communication"):
        raise Http404("Module communication non inclus dans l'offre de cette paroisse.")


class AnnonceListView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, ListView):
    model = Annonce
    template_name = "communication/annonce_liste.html"
    context_object_name = "annonces"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE
    module_requis = "communication"

    def get_queryset(self):
        return super().get_queryset().select_related("auteur", "groupe_cible")


class AnnonceDetailView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, DetailView):
    model = Annonce
    template_name = "communication/annonce_detail.html"
    context_object_name = "annonce"
    roles_autorises = ROLES_LECTURE
    module_requis = "communication"


class AnnonceCreateView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, CreateView):
    model = Annonce
    form_class = AnnonceForm
    template_name = "communication/annonce_form.html"
    roles_autorises = ROLES_ECRITURE
    module_requis = "communication"

    def form_valid(self, form):
        form.instance.auteur = self.request.user
        messages.success(self.request, "Annonce publiée.")
        return super().form_valid(form)


class AnnonceUpdateView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, UpdateView):
    model = Annonce
    form_class = AnnonceForm
    template_name = "communication/annonce_form.html"
    roles_autorises = ROLES_ECRITURE
    module_requis = "communication"

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class AnnonceDeleteView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, DeleteView):
    model = Annonce
    template_name = "communication/annonce_confirmer_suppression.html"
    success_url = reverse_lazy("communication:annonce_liste")
    roles_autorises = ROLES_ECRITURE
    module_requis = "communication"

    def form_valid(self, form):
        messages.success(self.request, "Annonce supprimée.")
        return super().form_valid(form)


class AnnoncePubliqueListView(ListView):
    """Page publique de la paroisse : consultable par n'importe quel
    visiteur, sans compte. Seules les annonces explicitement marquées
    `publique=True` y apparaissent — une paroisse suspendue n'a plus de
    page publique (§ suspension, apps.comptes)."""

    template_name = "communication/annonces_publiques.html"
    context_object_name = "annonces"
    paginate_by = 20

    def get_paroisse(self):
        paroisse = get_object_or_404(Paroisse, slug=self.kwargs["slug"], est_active=True)
        _verifier_module_communication(paroisse)
        return paroisse

    def get_queryset(self):
        self.paroisse = self.get_paroisse()
        return Annonce.objects.filter(paroisse=self.paroisse, publique=True).order_by(
            "-date_publication"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paroisse"] = self.paroisse
        return context


class AnnoncePubliqueDetailView(DetailView):
    template_name = "communication/annonce_publique_detail.html"
    context_object_name = "annonce"

    def get_queryset(self):
        paroisse = get_object_or_404(Paroisse, slug=self.kwargs["slug"], est_active=True)
        _verifier_module_communication(paroisse)
        return Annonce.objects.filter(paroisse=paroisse, publique=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paroisse"] = self.object.paroisse
        return context
