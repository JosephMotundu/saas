from django import forms

from apps.paroissiens.models import Paroissien

from .models import Don


class DonForm(forms.ModelForm):
    class Meta:
        model = Don
        fields = ["paroissien", "montant", "date", "type_don", "mode_paiement"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paroissien"].required = False
        if paroisse is not None:
            self.fields["paroissien"].queryset = Paroissien.objects.filter(paroisse=paroisse)
