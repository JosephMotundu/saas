from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView, View

from apps.comptes.mixins import FiltrageParoisseMixin, RoleRequisMixin

from .forms import DonForm
from .models import Don
from .services import enregistrer_don_avec_recu

ROLES_LECTURE = ("Trésorier", "Lecteur")
ROLES_ECRITURE = ("Trésorier",)


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
                date=form.cleaned_data["date"],
                type_don=form.cleaned_data["type_don"],
                mode_paiement=form.cleaned_data["mode_paiement"],
                paroissien=form.cleaned_data["paroissien"],
            )
            messages.success(request, f"Don enregistré, reçu fiscal {recu.numero} émis.")
            return redirect("finances:don_detail", pk=don.pk)
        return render(request, self.template_name, {"form": form})


class RecuFiscalView(RoleRequisMixin, View):
    roles_autorises = ROLES_LECTURE

    def get(self, request, pk):
        don = get_object_or_404(Don, pk=pk, paroisse=request.user.paroisse)
        return render(request, "finances/recu_certificat.html", {"don": don, "recu": don.recu_fiscal})
