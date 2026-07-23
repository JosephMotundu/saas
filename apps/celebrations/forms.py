from django import forms

from .models import Celebration, IntentionMesse


class CelebrationForm(forms.ModelForm):
    class Meta:
        model = Celebration
        fields = ["date", "heure", "type_celebration", "celebrant", "lieu"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "heure": forms.TimeInput(attrs={"type": "time"}),
        }


class IntentionMesseForm(forms.ModelForm):
    class Meta:
        model = IntentionMesse
        fields = ["celebration", "demandeur", "intention", "montant_offrande", "devise", "statut"]

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if paroisse is not None:
            self.fields["celebration"].queryset = Celebration.objects.filter(paroisse=paroisse)
