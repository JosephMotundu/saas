from django import forms

from apps.paroissiens.models import Paroissien

from .models import Depense, Don, OffrandeMesse


class DonForm(forms.ModelForm):
    class Meta:
        model = Don
        fields = ["paroissien", "montant", "devise", "date", "type_don", "mode_paiement"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paroissien"].required = False
        if paroisse is not None:
            self.fields["paroissien"].queryset = Paroissien.objects.filter(paroisse=paroisse)


class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ["libelle", "montant", "devise", "date", "categorie", "mode_paiement", "beneficiaire"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class OffrandeMesseForm(forms.ModelForm):
    class Meta:
        model = OffrandeMesse
        fields = ["libelle", "montant", "devise", "date", "mode_paiement"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
