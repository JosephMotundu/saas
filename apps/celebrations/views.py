from django.contrib import messages
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.comptes.mixins import FiltrageParoisseMixin, RoleRequisMixin

from .forms import CelebrationForm, IntentionMesseForm
from .models import Celebration, IntentionMesse

ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)


class CelebrationListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Celebration
    template_name = "celebrations/celebration_liste.html"
    context_object_name = "celebrations"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().order_by("date", "heure")


class CelebrationDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = Celebration
    template_name = "celebrations/celebration_detail.html"
    context_object_name = "celebration"
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().prefetch_related("intentions")


class CelebrationCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = Celebration
    form_class = CelebrationForm
    template_name = "celebrations/celebration_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Célébration enregistrée.")
        return super().form_valid(form)


class CelebrationUpdateView(RoleRequisMixin, FiltrageParoisseMixin, UpdateView):
    model = Celebration
    form_class = CelebrationForm
    template_name = "celebrations/celebration_form.html"
    roles_autorises = ROLES_ECRITURE

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)


class IntentionMesseListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = IntentionMesse
    template_name = "celebrations/intention_liste.html"
    context_object_name = "intentions"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE

    def get_queryset(self):
        return super().get_queryset().select_related("celebration")


class IntentionMesseDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    model = IntentionMesse
    template_name = "celebrations/intention_detail.html"
    context_object_name = "intention"
    roles_autorises = ROLES_LECTURE


class IntentionMesseCreateView(RoleRequisMixin, FiltrageParoisseMixin, CreateView):
    model = IntentionMesse
    form_class = IntentionMesseForm
    template_name = "celebrations/intention_form.html"
    roles_autorises = ROLES_ECRITURE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Intention de messe enregistrée.")
        return super().form_valid(form)


class IntentionMesseUpdateView(RoleRequisMixin, FiltrageParoisseMixin, UpdateView):
    model = IntentionMesse
    form_class = IntentionMesseForm
    template_name = "celebrations/intention_form.html"
    roles_autorises = ROLES_ECRITURE

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Modifications enregistrées.")
        return super().form_valid(form)
