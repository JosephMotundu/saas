from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import FormView, TemplateView

from apps.comptes.models import Abonnement, Paroisse, Utilisateur
from apps.finances.models import Don
from apps.paroissiens.models import Paroissien
from apps.sacrements.models import Bapteme, Communion, Confirmation, Funerailles, Mariage

from .forms import OFFRES, InscriptionForm
from .models import ContenuVitrine


class AccueilView(TemplateView):
    template_name = "core/accueil.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contenu"] = ContenuVitrine.charger()
        return context


class FonctionnalitesView(TemplateView):
    template_name = "core/fonctionnalites.html"


class TarifsView(TemplateView):
    template_name = "core/tarifs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["offres"] = [
            (valeur, libelle, Abonnement.LIMITES[valeur]) for valeur, libelle in OFFRES
        ]
        return context


class InscriptionView(FormView):
    """Souscription réelle : crée la paroisse, son abonnement et le compte
    du premier Curé dans une même transaction, puis connecte directement
    l'utilisateur. Pas de paiement — l'offre est activée immédiatement."""

    template_name = "core/souscription.html"
    form_class = InscriptionForm

    def get_initial(self):
        initial = super().get_initial()
        offre_demandee = self.request.GET.get("offre")
        if offre_demandee in dict(OFFRES):
            initial["offre"] = offre_demandee
        return initial

    def form_valid(self, form):
        donnees = form.cleaned_data
        adresse_composee = ", ".join(
            partie
            for partie in [donnees["avenue"], donnees.get("quartier"), donnees["commune"]]
            if partie
        )
        with transaction.atomic():
            paroisse = Paroisse.objects.create(
                nom=donnees["nom_paroisse"],
                diocese=donnees["diocese"],
                adresse=adresse_composee,
                ville=donnees["ville"],
                commune=donnees["commune"],
                quartier=donnees.get("quartier", ""),
                avenue=donnees["avenue"],
                email=donnees["email"],
                latitude=donnees.get("latitude"),
                longitude=donnees.get("longitude"),
            )
            Abonnement.objects.create(paroisse=paroisse, offre=donnees["offre"])
            cure = Utilisateur.objects.create_user(
                username=donnees["nom_utilisateur"],
                password=donnees["mot_de_passe"],
                first_name=donnees["prenom"],
                last_name=donnees["nom"],
                email=donnees["email"],
                paroisse=paroisse,
            )
            cure.groups.add(Group.objects.get(name="Curé"))

        login(self.request, cure)
        messages.success(self.request, f"Bienvenue ! {paroisse.nom} est prêt.")
        return redirect("core:tableau_de_bord")


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    template_name = "core/tableau_de_bord.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser and request.user.paroisse is None:
            return redirect("plateforme:paroisse_liste")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paroisse = self.request.user.paroisse
        context["paroisse"] = paroisse

        if paroisse is None:
            context["nombre_utilisateurs"] = 0
            context["nombre_paroissiens"] = 0
            context["nombre_actes_sacrements"] = 0
            context["nombre_dons"] = 0
            return context

        context["nombre_utilisateurs"] = Utilisateur.objects.filter(paroisse=paroisse).count()
        context["nombre_paroissiens"] = Paroissien.objects.filter(paroisse=paroisse).count()
        context["nombre_actes_sacrements"] = sum(
            modele.objects.filter(paroisse=paroisse).count()
            for modele in (Bapteme, Communion, Confirmation, Funerailles, Mariage)
        )
        context["nombre_dons"] = Don.objects.filter(paroisse=paroisse).count()
        return context
