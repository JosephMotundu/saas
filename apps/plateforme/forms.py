from django import forms

from apps.core.models import ContenuVitrine


class ContenuVitrineForm(forms.ModelForm):
    class Meta:
        model = ContenuVitrine
        fields = ["titre_hero", "accroche_hero", "image_hero", "titre_cta", "texte_cta"]
        widgets = {"accroche_hero": forms.Textarea(attrs={"rows": 4})}
