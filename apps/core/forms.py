from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.comptes.models import Abonnement, Paroisse, Utilisateur

OFFRES = Abonnement.OFFRE_CHOICES


class InscriptionForm(forms.Form):
    """Inscription self-service : crée réellement la paroisse, son
    abonnement et le compte du premier Curé (transaction atomique, voir
    apps.core.views.InscriptionView). Pas de paiement — l'offre choisie est
    activée immédiatement, en mode démonstration."""

    # Paroisse
    nom_paroisse = forms.CharField(label="Nom de la paroisse", max_length=200)
    diocese = forms.CharField(label="Diocèse", max_length=200)
    adresse = forms.CharField(label="Adresse", max_length=255)
    ville = forms.CharField(label="Ville", max_length=100)
    offre = forms.ChoiceField(label="Offre choisie", choices=OFFRES)

    # Compte administrateur (premier Curé)
    prenom = forms.CharField(label="Prénom")
    nom = forms.CharField(label="Nom")
    email = forms.EmailField(label="Email")
    nom_utilisateur = forms.CharField(label="Nom d'utilisateur", max_length=150)
    mot_de_passe = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    mot_de_passe_confirmation = forms.CharField(
        label="Confirmer le mot de passe", widget=forms.PasswordInput
    )

    def clean_nom_paroisse(self):
        nom_paroisse = self.cleaned_data["nom_paroisse"]
        if Paroisse.objects.filter(nom__iexact=nom_paroisse).exists():
            raise ValidationError("Une paroisse porte déjà ce nom.")
        return nom_paroisse

    def clean_nom_utilisateur(self):
        nom_utilisateur = self.cleaned_data["nom_utilisateur"]
        if Utilisateur.objects.filter(username__iexact=nom_utilisateur).exists():
            raise ValidationError("Ce nom d'utilisateur est déjà pris.")
        return nom_utilisateur

    def clean(self):
        cleaned_data = super().clean()
        mot_de_passe = cleaned_data.get("mot_de_passe")
        confirmation = cleaned_data.get("mot_de_passe_confirmation")
        if mot_de_passe and confirmation and mot_de_passe != confirmation:
            self.add_error(
                "mot_de_passe_confirmation", "Les mots de passe ne correspondent pas."
            )
        if mot_de_passe:
            try:
                validate_password(mot_de_passe)
            except ValidationError as erreur:
                self.add_error("mot_de_passe", erreur)
        return cleaned_data
