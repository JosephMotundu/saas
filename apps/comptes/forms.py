from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group

from .models import Abonnement, Utilisateur


class ConnexionForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {
                "class": "champ-saisie",
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "Nom d'utilisateur",
            }
        )
        self.fields["password"].widget.attrs.update(
            {
                "class": "champ-saisie",
                "autocomplete": "current-password",
                "placeholder": "Mot de passe",
            }
        )

    error_messages = {
        "invalid_login": (
            "Identifiants invalides. Vérifiez le nom d'utilisateur et le mot de passe."
        ),
        "inactive": "Ce compte a été désactivé.",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.paroisse is not None and not user.paroisse.est_active:
            raise forms.ValidationError(
                "Votre paroisse a été suspendue. Contactez l'administrateur de "
                "la plateforme.",
                code="paroisse_suspendue",
            )


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ["first_name", "last_name", "email"]
        labels = {"first_name": "Prénom", "last_name": "Nom", "email": "Email"}


ROLES_INVITABLES = [
    ("Curé", "Curé"),
    ("Secrétaire", "Secrétaire"),
    ("Trésorier", "Trésorier"),
    ("Lecteur", "Lecteur"),
]


class InvitationForm(forms.Form):
    """Le Curé invite un collaborateur : il choisit son rôle, le compte est
    créé avec un mot de passe temporaire généré par le serveur (jamais
    choisi par l'inviteur)."""

    prenom = forms.CharField(label="Prénom")
    nom = forms.CharField(label="Nom")
    email = forms.EmailField(label="Email")
    nom_utilisateur = forms.CharField(label="Nom d'utilisateur", max_length=150)
    role = forms.ChoiceField(label="Rôle", choices=ROLES_INVITABLES)

    def clean_nom_utilisateur(self):
        nom_utilisateur = self.cleaned_data["nom_utilisateur"]
        if Utilisateur.objects.filter(username__iexact=nom_utilisateur).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return nom_utilisateur

    def clean_role(self):
        role = self.cleaned_data["role"]
        if not Group.objects.filter(name=role).exists():
            raise forms.ValidationError("Rôle inconnu.")
        return role


class ChangerOffreForm(forms.Form):
    offre = forms.ChoiceField(label="Offre", choices=Abonnement.OFFRE_CHOICES)
