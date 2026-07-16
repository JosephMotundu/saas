from django import forms

from apps.core.models import ContenuVitrine


class ContenuVitrineForm(forms.ModelForm):
    class Meta:
        model = ContenuVitrine
        fields = ["titre_hero", "accroche_hero", "image_hero", "titre_cta", "texte_cta"]
        widgets = {"accroche_hero": forms.Textarea(attrs={"rows": 4})}


class ParoisseSupprimerForm(forms.Form):
    """Exige de retaper le nom exact de la paroisse : dernier garde-fou avant
    une suppression irréversible de toutes ses données."""

    confirmation = forms.CharField(label="Nom de la paroisse, pour confirmer")

    def __init__(self, *args, paroisse=None, **kwargs):
        self.paroisse = paroisse
        super().__init__(*args, **kwargs)

    def clean_confirmation(self):
        valeur = self.cleaned_data["confirmation"]
        if valeur.strip() != self.paroisse.nom:
            raise forms.ValidationError(
                "Le nom saisi ne correspond pas à celui de la paroisse."
            )
        return valeur
