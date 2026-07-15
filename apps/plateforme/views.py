import secrets

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, UpdateView, View

from apps.comptes.models import Paroisse, Utilisateur
from apps.core.models import ContenuVitrine
from apps.finances.models import Don
from apps.paroissiens.models import Paroissien
from apps.sacrements.models import Bapteme, Communion, Confirmation, Funerailles, Mariage

from .forms import ContenuVitrineForm
from .mixins import SuperuserRequisMixin


class ParoisseListView(SuperuserRequisMixin, ListView):
    model = Paroisse
    template_name = "plateforme/paroisse_liste.html"
    context_object_name = "paroisses"

    def get_queryset(self):
        return (
            Paroisse.objects.select_related("abonnement")
            .annotate(
                nombre_utilisateurs=Count("utilisateurs", distinct=True),
                nombre_paroissiens=Count("paroissiens", distinct=True),
            )
            .order_by("nom")
        )


class ParoisseDetailView(SuperuserRequisMixin, DetailView):
    model = Paroisse
    template_name = "plateforme/paroisse_detail.html"
    context_object_name = "paroisse"

    def get_queryset(self):
        return Paroisse.objects.select_related("abonnement")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paroisse = self.object
        context["membres"] = (
            Utilisateur.objects.filter(paroisse=paroisse)
            .prefetch_related("groups")
            .order_by("username")
        )
        context["nombre_paroissiens"] = Paroissien.objects.filter(paroisse=paroisse).count()
        context["nombre_actes_sacrements"] = sum(
            modele.objects.filter(paroisse=paroisse).count()
            for modele in (Bapteme, Communion, Confirmation, Funerailles, Mariage)
        )
        context["nombre_dons"] = Don.objects.filter(paroisse=paroisse).count()
        return context


class ParoisseBasculerActiveView(SuperuserRequisMixin, View):
    def post(self, request, pk):
        paroisse = get_object_or_404(Paroisse, pk=pk)
        paroisse.est_active = not paroisse.est_active
        paroisse.save(update_fields=["est_active"])
        etat = "réactivée" if paroisse.est_active else "suspendue"
        messages.success(request, f"Paroisse {paroisse.nom} {etat}.")
        return redirect("plateforme:paroisse_detail", pk=paroisse.pk)


class MembreReinitialiserMotDePasseView(SuperuserRequisMixin, View):
    def post(self, request, pk):
        membre = get_object_or_404(Utilisateur, pk=pk, paroisse__isnull=False)
        mot_de_passe_temporaire = secrets.token_urlsafe(9)
        membre.set_password(mot_de_passe_temporaire)
        membre.save()
        return render(
            request,
            "plateforme/membre_mot_de_passe_reinitialise.html",
            {"membre": membre, "mot_de_passe_temporaire": mot_de_passe_temporaire},
        )


class VitrineModifierView(SuperuserRequisMixin, UpdateView):
    form_class = ContenuVitrineForm
    template_name = "plateforme/vitrine_modifier.html"
    success_url = reverse_lazy("plateforme:vitrine_modifier")

    def get_object(self, queryset=None):
        return ContenuVitrine.charger()

    def form_valid(self, form):
        messages.success(self.request, "Page d'accueil mise à jour.")
        return super().form_valid(form)
