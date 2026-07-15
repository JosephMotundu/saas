from django import forms
from django.contrib.auth.models import Group

from .models import Annonce


class AnnonceForm(forms.ModelForm):
    class Meta:
        model = Annonce
        fields = ["titre", "contenu", "date_publication", "groupe_cible", "publique"]
        widgets = {"date_publication": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groupe_cible"].queryset = Group.objects.all()
        self.fields["groupe_cible"].required = False
