from django import forms

OFFRES = [
    ("essentiel", "Essentiel"),
    ("standard", "Standard"),
    ("diocese", "Diocèse"),
]


class SouscriptionForm(forms.Form):
    """Formulaire de démonstration : simule une demande d'abonnement.

    Aucun paiement n'est traité. Aucune clé ou identifiant de prestataire de
    paiement n'est utilisé ici ; le jour où un vrai prestataire (sandbox) sera
    branché, ses clés viendront exclusivement des variables d'environnement.
    """

    nom_paroisse = forms.CharField(label="Nom de la paroisse", max_length=200)
    diocese = forms.CharField(label="Diocèse", max_length=200)
    ville = forms.CharField(label="Ville", max_length=100)
    email_contact = forms.EmailField(label="Email de contact")
    offre = forms.ChoiceField(label="Offre choisie", choices=OFFRES)
