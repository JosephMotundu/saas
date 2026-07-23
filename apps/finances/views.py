from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView, TemplateView, View

from apps.comptes.mixins import FiltrageParoisseMixin, RoleRequisMixin

from .forms import DepenseForm, DonForm, OffrandeMesseForm
from .models import Depense, Don, OffrandeMesse
from .services import calculer_situation_financiere, enregistrer_don_avec_recu

ROLES_LECTURE = ("Trésorier", "Lecteur")
ROLES_ECRITURE = ("Trésorier",)


class TableauFinancierView(RoleRequisMixin, TemplateView):
    """Accueil du module finances : affiche le solde calculé automatiquement
    (recettes − dépenses) et la ventilation par type/catégorie."""

    template_name = "finances/tableau.html"
    roles_autorises = ROLES_LECTURE

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["situation"] = calculer_situation_financiere(self.request.paroisse)
        return contexte


class DonListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Don
    template_name = "finances/don_liste.html"
    context_object_name = "dons"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien")


class DonDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Don
    template_name = "finances/don_detail.html"
    context_object_name = "don"
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien", "recu_fiscal")


class DonCreateView(RoleRequisMixin, View):
    """N'utilise pas CreateView : la création du Don et de son RecuFiscal se
    fait dans une même transaction via services.enregistrer_don_avec_recu
    (§14 du brief)."""

    roles_autorises = ROLES_ECRITURE
    template_name = "finances/don_form.html"

    def get(self, request):
        form = DonForm(paroisse=request.user.paroisse)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = DonForm(request.POST, paroisse=request.user.paroisse)
        if form.is_valid():
            don, recu = enregistrer_don_avec_recu(
                paroisse=request.user.paroisse,
                montant=form.cleaned_data["montant"],
                devise=form.cleaned_data["devise"],
                date=form.cleaned_data["date"],
                type_don=form.cleaned_data["type_don"],
                mode_paiement=form.cleaned_data["mode_paiement"],
                paroissien=form.cleaned_data["paroissien"],
            )
            messages.success(request, f"Don enregistré, reçu fiscal {recu.numero} émis.")
            return redirect("finances:don_detail", pk=don.pk)
        return render(request, self.template_name, {"form": form})


class DepenseListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Depense
    template_name = "finances/depense_liste.html"
    context_object_name = "depenses"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE


class DepenseDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Depense
    template_name = "finances/depense_detail.html"
    context_object_name = "depense"
    roles_autorises = ROLES_LECTURE


class DepenseCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = Depense
    form_class = DepenseForm
    template_name = "finances/depense_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        reponse = super().form_valid(form)
        messages.success(self.request, "Dépense enregistrée.")
        return reponse


class OffrandeMesseListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = OffrandeMesse
    template_name = "finances/offrande_liste.html"
    context_object_name = "offrandes"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE


class OffrandeMesseDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = OffrandeMesse
    template_name = "finances/offrande_detail.html"
    context_object_name = "offrande"
    roles_autorises = ROLES_LECTURE


class OffrandeMesseCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = OffrandeMesse
    form_class = OffrandeMesseForm
    template_name = "finances/offrande_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        reponse = super().form_valid(form)
        messages.success(self.request, "Offrande de messe enregistrée.")
        return reponse


class RecuFiscalView(RoleRequisMixin, View):
    roles_autorises = ROLES_LECTURE

    def get(self, request, pk):
        don = get_object_or_404(Don, pk=pk, paroisse=request.user.paroisse)
        return render(request, "finances/recu_certificat.html", {"don": don, "recu": don.recu_fiscal})
