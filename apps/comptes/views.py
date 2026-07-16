import secrets

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, UpdateView, View

from .forms import (
    ChangerOffreForm,
    ConnexionForm,
    InvitationForm,
    MembreModifierForm,
    ProfilForm,
)
from .mixins import ExigeParoisseMixin, FiltrageParoisseMixin, RoleRequisMixin
from .models import Abonnement, Utilisateur


class ConnexionView(LoginView):
    template_name = "comptes/connexion.html"
    form_class = ConnexionForm
    redirect_authenticated_user = True


class ProfilView(LoginRequiredMixin, TemplateView):
    template_name = "comptes/profil.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = list(self.request.user.groups.values_list("name", flat=True))
        return context


class ProfilModifierView(LoginRequiredMixin, UpdateView):
    model = Utilisateur
    form_class = ProfilForm
    template_name = "comptes/profil_modifier.html"
    success_url = reverse_lazy("comptes:profil")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profil mis à jour.")
        return super().form_valid(form)


class EquipeListView(FiltrageParoisseMixin, ListView):
    model = Utilisateur
    template_name = "comptes/equipe_liste.html"
    context_object_name = "membres"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("groups").order_by("username")


class InvitationCreateView(RoleRequisMixin, ExigeParoisseMixin, View):
    """Réservé au Curé : crée un compte pour un collaborateur avec un mot
    de passe temporaire généré côté serveur (jamais choisi par l'inviteur),
    affiché une seule fois pour être communiqué à la personne invitée."""

    roles_autorises = ()
    template_name = "comptes/equipe_inviter.html"

    def get(self, request):
        return render(request, self.template_name, {"form": InvitationForm()})

    def post(self, request):
        form = InvitationForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        donnees = form.cleaned_data
        abonnement = getattr(request.paroisse, "abonnement", None)
        if abonnement is not None and donnees["role"] != "Curé":
            limite = abonnement.max_utilisateurs_supplementaires()
            if limite is not None:
                compte_actuel = (
                    Utilisateur.objects.filter(paroisse=request.paroisse)
                    .exclude(groups__name="Curé")
                    .count()
                )
                if compte_actuel >= limite:
                    messages.error(
                        request,
                        f"Votre offre {abonnement.get_offre_display()} est limitée à "
                        f"{limite} utilisateurs en plus du Curé. Passez à une offre "
                        "supérieure pour en inviter davantage.",
                    )
                    return redirect("comptes:equipe")

        mot_de_passe_temporaire = secrets.token_urlsafe(9)
        membre = Utilisateur.objects.create_user(
            username=donnees["nom_utilisateur"],
            password=mot_de_passe_temporaire,
            first_name=donnees["prenom"],
            last_name=donnees["nom"],
            email=donnees["email"],
            paroisse=request.paroisse,
        )
        membre.groups.add(Group.objects.get(name=donnees["role"]))

        return render(
            request,
            "comptes/equipe_invitation_confirmee.html",
            {"membre": membre, "mot_de_passe_temporaire": mot_de_passe_temporaire},
        )


class MembreBasculerActifView(RoleRequisMixin, ExigeParoisseMixin, View):
    roles_autorises = ()

    def post(self, request, pk):
        membre = get_object_or_404(Utilisateur, pk=pk, paroisse=request.paroisse)
        if membre == request.user:
            messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
        else:
            membre.is_active = not membre.is_active
            membre.save(update_fields=["is_active"])
            etat = "réactivé" if membre.is_active else "désactivé"
            messages.success(request, f"Compte de {membre} {etat}.")
        return redirect("comptes:equipe")


class MembreModifierView(RoleRequisMixin, ExigeParoisseMixin, View):
    """Réservé au Curé : modifie les coordonnées et le rôle d'un membre de
    son équipe. Le nom d'utilisateur reste stable ; on passe par « Mon
    compte » pour se modifier soi-même, pas par ici."""

    roles_autorises = ()
    template_name = "comptes/equipe_modifier.html"

    def get_membre(self, request, pk):
        return get_object_or_404(Utilisateur, pk=pk, paroisse=request.paroisse)

    def get(self, request, pk):
        membre = self.get_membre(request, pk)
        if membre == request.user:
            messages.error(request, "Modifiez votre propre profil depuis « Mon compte ».")
            return redirect("comptes:equipe")
        role_actuel = membre.groups.values_list("name", flat=True).first()
        form = MembreModifierForm(
            initial={
                "prenom": membre.first_name,
                "nom": membre.last_name,
                "email": membre.email,
                "role": role_actuel,
            }
        )
        return render(request, self.template_name, {"form": form, "membre": membre})

    def post(self, request, pk):
        membre = self.get_membre(request, pk)
        if membre == request.user:
            messages.error(request, "Modifiez votre propre profil depuis « Mon compte ».")
            return redirect("comptes:equipe")

        form = MembreModifierForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "membre": membre})

        donnees = form.cleaned_data
        membre.first_name = donnees["prenom"]
        membre.last_name = donnees["nom"]
        membre.email = donnees["email"]
        membre.save(update_fields=["first_name", "last_name", "email"])
        membre.groups.set([Group.objects.get(name=donnees["role"])])

        messages.success(request, f"Compte de {membre} mis à jour.")
        return redirect("comptes:equipe")


class MembreReinitialiserMotDePasseView(RoleRequisMixin, ExigeParoisseMixin, View):
    """Réservé au Curé : réinitialise le mot de passe d'un membre de sa
    propre paroisse (pas besoin de solliciter le superadmin de la
    plateforme pour ça — voir aussi apps.plateforme, réservé au
    superadmin pour n'importe quelle paroisse)."""

    roles_autorises = ()

    def post(self, request, pk):
        membre = get_object_or_404(Utilisateur, pk=pk, paroisse=request.paroisse)
        if membre == request.user:
            messages.error(request, "Changez votre propre mot de passe depuis « Mon compte ».")
            return redirect("comptes:equipe")

        mot_de_passe_temporaire = secrets.token_urlsafe(9)
        membre.set_password(mot_de_passe_temporaire)
        membre.save()

        return render(
            request,
            "comptes/equipe_mot_de_passe_reinitialise.html",
            {"membre": membre, "mot_de_passe_temporaire": mot_de_passe_temporaire},
        )


class AbonnementView(RoleRequisMixin, ExigeParoisseMixin, TemplateView):
    roles_autorises = ()
    template_name = "comptes/abonnement.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        abonnement = self.request.paroisse.abonnement
        context["abonnement"] = abonnement
        context["limites"] = abonnement.limites()
        context["toutes_les_offres"] = [
            (valeur, libelle, Abonnement.LIMITES[valeur]) for valeur, libelle in Abonnement.OFFRE_CHOICES
        ]
        context.setdefault("form", ChangerOffreForm(initial={"offre": abonnement.offre}))
        return context

    def post(self, request):
        abonnement = request.paroisse.abonnement
        form = ChangerOffreForm(request.POST)
        if form.is_valid():
            abonnement.offre = form.cleaned_data["offre"]
            abonnement.save(update_fields=["offre"])
            messages.success(request, "Offre mise à jour.")
            return redirect("comptes:abonnement")
        return self.render_to_response(self.get_context_data(form=form))


class AbonnementBasculerStatutView(RoleRequisMixin, ExigeParoisseMixin, View):
    roles_autorises = ()

    def post(self, request):
        abonnement = request.paroisse.abonnement
        if abonnement.statut == "actif":
            abonnement.annuler()
            messages.success(request, "Abonnement annulé.")
        else:
            abonnement.reactiver()
            messages.success(request, "Abonnement réactivé.")
        return redirect("comptes:abonnement")
