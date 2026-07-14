from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from apps.comptes.mixins import FiltrageParoisseMixin, RoleRequisMixin

from .forms import (
    BaptemeForm,
    CommunionForm,
    ConfirmationForm,
    FunraillesForm,
    MariageForm,
    MentionMarginaleForm,
)
from .models import Bapteme, Communion, Confirmation, Funerailles, Mariage

ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)


class SacrementsIndexView(RoleRequisMixin, TemplateView):
    template_name = "sacrements/index.html"
    roles_autorises = ROLES_LECTURE


class ActePersonnelMixin:
    """Factorise les vues de registre communes à Baptême, Communion,
    Confirmation et Funérailles : même gabarit, seul le modèle change."""

    type_url = ""
    nom_singulier = ""
    nom_pluriel = ""
    template_liste = "sacrements/acte_liste.html"
    template_detail = "sacrements/acte_detail.html"
    template_form = "sacrements/acte_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            type_url=self.type_url,
            nom_singulier=self.nom_singulier,
            nom_pluriel=self.nom_pluriel,
        )
        return context


class CertificatMixin(RoleRequisMixin):
    roles_autorises = ROLES_LECTURE
    modele = None
    type_url = ""
    template_certificat = "sacrements/acte_certificat.html"

    def get(self, request, pk):
        acte = get_object_or_404(self.modele, pk=pk, paroisse=request.user.paroisse)
        return render(
            request, self.template_certificat, {"acte": acte, "type_url": self.type_url}
        )


# ---------- Baptême ----------


class BaptemeListView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, ListView):
    model = Bapteme
    context_object_name = "actes"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "bapteme", "Baptême", "Baptêmes"

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien")

    def get_template_names(self):
        return [self.template_liste]


class BaptemeDetailView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, DetailView):
    model = Bapteme
    context_object_name = "acte"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "bapteme", "Baptême", "Baptêmes"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("paroissien")
            .prefetch_related("mentions_marginales")
        )

    def get_template_names(self):
        return [self.template_detail]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formulaire_mention"] = MentionMarginaleForm()
        return context


class BaptemeCreateView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, CreateView):
    model = Bapteme
    form_class = BaptemeForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "bapteme", "Baptême", "Baptêmes"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Baptême enregistré au registre.")
        return super().form_valid(form)


class BaptemeUpdateView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, UpdateView):
    model = Bapteme
    form_class = BaptemeForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "bapteme", "Baptême", "Baptêmes"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class BaptemeCertificatView(CertificatMixin, View):
    modele = Bapteme
    type_url = "bapteme"


class MentionMarginaleCreateView(RoleRequisMixin, View):
    roles_autorises = ROLES_ECRITURE

    def post(self, request, pk):
        bapteme = get_object_or_404(Bapteme, pk=pk, paroisse=request.user.paroisse)
        formulaire = MentionMarginaleForm(request.POST)
        if formulaire.is_valid():
            mention = formulaire.save(commit=False)
            mention.bapteme = bapteme
            mention.paroisse = request.user.paroisse
            mention.save()
            messages.success(request, "Mention marginale ajoutée.")
        else:
            messages.error(request, "La mention marginale n'a pas pu être ajoutée.")
        return redirect("sacrements:bapteme_detail", pk=bapteme.pk)


# ---------- Communion ----------


class CommunionListView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, ListView):
    model = Communion
    context_object_name = "actes"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "communion", "Communion", "Communions"

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien")

    def get_template_names(self):
        return [self.template_liste]


class CommunionDetailView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, DetailView):
    model = Communion
    context_object_name = "acte"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "communion", "Communion", "Communions"

    def get_template_names(self):
        return [self.template_detail]


class CommunionCreateView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, CreateView):
    model = Communion
    form_class = CommunionForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "communion", "Communion", "Communions"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Communion enregistrée au registre.")
        return super().form_valid(form)


class CommunionUpdateView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, UpdateView):
    model = Communion
    form_class = CommunionForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "communion", "Communion", "Communions"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class CommunionCertificatView(CertificatMixin, View):
    modele = Communion
    type_url = "communion"


# ---------- Confirmation ----------


class ConfirmationListView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, ListView):
    model = Confirmation
    context_object_name = "actes"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "confirmation", "Confirmation", "Confirmations"

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien")

    def get_template_names(self):
        return [self.template_liste]


class ConfirmationDetailView(
    RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, DetailView
):
    model = Confirmation
    context_object_name = "acte"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "confirmation", "Confirmation", "Confirmations"

    def get_template_names(self):
        return [self.template_detail]


class ConfirmationCreateView(
    RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, CreateView
):
    model = Confirmation
    form_class = ConfirmationForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "confirmation", "Confirmation", "Confirmations"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Confirmation enregistrée au registre.")
        return super().form_valid(form)


class ConfirmationUpdateView(
    RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, UpdateView
):
    model = Confirmation
    form_class = ConfirmationForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "confirmation", "Confirmation", "Confirmations"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class ConfirmationCertificatView(CertificatMixin, View):
    modele = Confirmation
    type_url = "confirmation"


# ---------- Funérailles ----------


class FunraillesListView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, ListView):
    model = Funerailles
    context_object_name = "actes"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "funerailles", "Funérailles", "Funérailles"

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien")

    def get_template_names(self):
        return [self.template_liste]


class FunraillesDetailView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, DetailView):
    model = Funerailles
    context_object_name = "acte"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "funerailles", "Funérailles", "Funérailles"

    def get_template_names(self):
        return [self.template_detail]


class FunraillesCreateView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, CreateView):
    model = Funerailles
    form_class = FunraillesForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "funerailles", "Funérailles", "Funérailles"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Funérailles enregistrées au registre.")
        return super().form_valid(form)


class FunraillesUpdateView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, UpdateView):
    model = Funerailles
    form_class = FunraillesForm
    roles_autorises = ROLES_ECRITURE
    type_url, nom_singulier, nom_pluriel = "funerailles", "Funérailles", "Funérailles"

    def get_template_names(self):
        return [self.template_form]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class FunraillesCertificatView(CertificatMixin, View):
    modele = Funerailles
    type_url = "funerailles"


# ---------- Mariage ----------


class MariageListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Mariage
    context_object_name = "mariages"
    template_name = "sacrements/mariage_liste.html"
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("conjoint1", "conjoint2")


class MariageDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Mariage
    context_object_name = "mariage"
    template_name = "sacrements/mariage_detail.html"
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("conjoint1", "conjoint2")


class MariageCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = Mariage
    form_class = MariageForm
    template_name = "sacrements/mariage_form.html"
    roles_autorises = ROLES_ECRITURE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Mariage enregistré au registre.")
        return super().form_valid(form)


class MariageUpdateView(RoleRequisMixin, FiltrageParoisseMixin, UpdateView):
    model = Mariage
    form_class = MariageForm
    template_name = "sacrements/mariage_form.html"
    roles_autorises = ROLES_ECRITURE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class MariageCertificatView(RoleRequisMixin, View):
    roles_autorises = ROLES_LECTURE

    def get(self, request, pk):
        mariage = get_object_or_404(Mariage, pk=pk, paroisse=request.user.paroisse)
        return render(request, "sacrements/mariage_certificat.html", {"mariage": mariage})
