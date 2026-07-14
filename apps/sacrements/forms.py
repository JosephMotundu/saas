from django import forms

from apps.paroissiens.models import Paroissien

from .models import Bapteme, Communion, Confirmation, Funerailles, Mariage, MentionMarginale


class _FormActeParoissienMixin:
    """Restreint le choix du paroissien (et des conjoints) à la paroisse
    courante ; évite qu'un secrétariat n'enregistre un acte pour une
    personne d'une autre paroisse."""

    champs_paroissien = ["paroissien"]

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if paroisse is not None:
            queryset = Paroissien.objects.filter(paroisse=paroisse)
            for nom_champ in self.champs_paroissien:
                self.fields[nom_champ].queryset = queryset
        self.fields["date"].widget = forms.DateInput(attrs={"type": "date"})


class BaptemeForm(_FormActeParoissienMixin, forms.ModelForm):
    class Meta:
        model = Bapteme
        fields = ["paroissien", "date", "lieu", "celebrant", "parrain", "marraine"]


class CommunionForm(_FormActeParoissienMixin, forms.ModelForm):
    class Meta:
        model = Communion
        fields = ["paroissien", "date", "lieu", "celebrant"]


class ConfirmationForm(_FormActeParoissienMixin, forms.ModelForm):
    class Meta:
        model = Confirmation
        fields = ["paroissien", "date", "lieu", "celebrant"]


class FunraillesForm(_FormActeParoissienMixin, forms.ModelForm):
    class Meta:
        model = Funerailles
        fields = ["paroissien", "date", "lieu", "celebrant"]


class MariageForm(_FormActeParoissienMixin, forms.ModelForm):
    champs_paroissien = ["conjoint1", "conjoint2"]

    class Meta:
        model = Mariage
        fields = ["conjoint1", "conjoint2", "date", "lieu", "celebrant", "temoins"]


class MentionMarginaleForm(forms.ModelForm):
    class Meta:
        model = MentionMarginale
        fields = ["type_mention", "date", "reference"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
