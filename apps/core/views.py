from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import FormView, TemplateView

from apps.comptes.models import Utilisateur

from .forms import OFFRES, SouscriptionForm


class AccueilView(TemplateView):
    template_name = "core/accueil.html"


class FonctionnalitesView(TemplateView):
    template_name = "core/fonctionnalites.html"


class TarifsView(TemplateView):
    template_name = "core/tarifs.html"


class SouscriptionView(FormView):
    template_name = "core/souscription.html"
    form_class = SouscriptionForm

    def get_initial(self):
        initial = super().get_initial()
        offre_demandee = self.request.GET.get("offre")
        if offre_demandee in dict(OFFRES):
            initial["offre"] = offre_demandee
        return initial

    def form_valid(self, form):
        # Démonstration uniquement : aucun paiement n'est traité, aucune
        # donnée n'est persistée. Le flux réel (sandbox) sera branché
        # ultérieurement sans exposer de clé secrète dans le code.
        offre_libelle = dict(OFFRES).get(form.cleaned_data["offre"], form.cleaned_data["offre"])
        return self.render_to_response(
            self.get_context_data(
                form=form, confirmation=form.cleaned_data, offre_libelle=offre_libelle
            )
        )


class TableauDeBordView(LoginRequiredMixin, TemplateView):
    template_name = "core/tableau_de_bord.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paroisse = self.request.user.paroisse
        context["paroisse"] = paroisse
        context["nombre_utilisateurs"] = (
            Utilisateur.objects.filter(paroisse=paroisse).count() if paroisse else 0
        )
        return context
