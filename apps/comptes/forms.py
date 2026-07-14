from django.contrib.auth.forms import AuthenticationForm


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
