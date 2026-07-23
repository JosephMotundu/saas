"""Devises partagées par le projet (finances, célébrations…).

Placé dans `core` — une app feuille sans dépendance métier — pour que
`finances` et `celebrations` s'y réfèrent sans créer de dépendance croisée.
Décision produit : dollars et francs ne sont jamais additionnés entre eux ;
chaque montant porte donc sa devise et le solde est calculé par devise.
"""

DEVISE_CHOICES = [
    ("CDF", "Franc congolais (FC)"),
    ("USD", "Dollar (USD)"),
]

SYMBOLES_DEVISE = {"CDF": "FC", "USD": "$"}


def formater_montant(montant, devise):
    """Rend un montant avec le symbole de sa devise, ex. « 45 FC », « 120 $ »."""
    return f"{montant} {SYMBOLES_DEVISE.get(devise, devise)}"
