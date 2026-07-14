from django import forms

from .models import Famille, Paroissien


class FamilleForm(forms.ModelForm):
    class Meta:
        model = Famille
        fields = ["nom", "adresse", "telephone"]


class ParoissienForm(forms.ModelForm):
    class Meta:
        model = Paroissien
        fields = [
            "nom",
            "prenom",
            "sexe",
            "date_naissance",
            "adresse",
            "telephone",
            "email",
            "photo",
            "famille",
        ]
        widgets = {"date_naissance": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if paroisse is not None:
            self.fields["famille"].queryset = Famille.objects.filter(paroisse=paroisse)
        self.fields["famille"].required = False
