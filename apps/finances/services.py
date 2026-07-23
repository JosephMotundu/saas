"""Logique métier réutilisable pour les finances (voir §9 du brief : couche
services pour les opérations qui dépassent un simple modèle)."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.celebrations.models import IntentionMesse
from apps.core.devises import DEVISE_CHOICES, SYMBOLES_DEVISE

from .models import Depense, Don, OffrandeMesse, RecuFiscal


def _totaux_par_devise(requete, champ_montant="montant"):
    """Renvoie {devise: total} pour une requête agrégée par devise."""
    lignes = requete.values("devise").annotate(total=Sum(champ_montant))
    return {ligne["devise"]: ligne["total"] or Decimal("0") for ligne in lignes}


def calculer_situation_financiere(paroisse):
    """Calcule automatiquement le solde d'une paroisse, séparément pour
    chaque devise (§ décision produit : pas de conversion, dollars et francs
    ne s'additionnent jamais entre eux).

    Les recettes proviennent de trois sources : les dons, les offrandes de
    messe (quêtes) et les offrandes des intentions de messe (hors intentions
    annulées). Renvoie une liste `par_devise` (recettes / dépenses / solde) et
    la ventilation des recettes par source et des dépenses par catégorie
    (§14 du brief — agrégations en base, un solde exact par devise)."""
    dons = _totaux_par_devise(Don.objects.filter(paroisse=paroisse))
    offrandes_messe = _totaux_par_devise(OffrandeMesse.objects.filter(paroisse=paroisse))
    offrandes_intentions = _totaux_par_devise(
        IntentionMesse.objects.filter(paroisse=paroisse)
        .exclude(statut="annulee")
        .exclude(montant_offrande__isnull=True),
        champ_montant="montant_offrande",
    )
    depenses = _totaux_par_devise(Depense.objects.filter(paroisse=paroisse))

    libelles = dict(DEVISE_CHOICES)
    par_devise = []
    for code, _ in DEVISE_CHOICES:
        recettes_devise = (
            dons.get(code, Decimal("0"))
            + offrandes_messe.get(code, Decimal("0"))
            + offrandes_intentions.get(code, Decimal("0"))
        )
        depenses_devise = depenses.get(code, Decimal("0"))
        if not recettes_devise and not depenses_devise:
            continue  # devise sans aucun mouvement : on ne l'affiche pas
        par_devise.append(
            {
                "devise": code,
                "libelle": libelles[code],
                "symbole": SYMBOLES_DEVISE.get(code, code),
                "recettes": recettes_devise,
                "depenses": depenses_devise,
                "solde": recettes_devise - depenses_devise,
                "dons": dons.get(code, Decimal("0")),
                "offrandes_messe": offrandes_messe.get(code, Decimal("0")),
                "offrandes_intentions": offrandes_intentions.get(code, Decimal("0")),
            }
        )

    depenses_par_categorie = (
        Depense.objects.filter(paroisse=paroisse)
        .values("categorie", "devise")
        .annotate(total=Sum("montant"))
        .order_by("devise", "-total")
    )

    return {
        "par_devise": par_devise,
        "depenses_par_categorie": list(depenses_par_categorie),
    }


@transaction.atomic
def enregistrer_don_avec_recu(
    *, paroisse, montant, date, type_don, mode_paiement, devise="CDF", paroissien=None
):
    """Crée un Don et son RecuFiscal dans une même transaction : soit les
    deux existent, soit aucun (§14 du brief — opération critique)."""
    don = Don.objects.create(
        paroisse=paroisse,
        montant=montant,
        devise=devise,
        date=date,
        type_don=type_don,
        mode_paiement=mode_paiement,
        paroissien=paroissien,
    )
    recu = RecuFiscal.objects.create(don=don, date_emission=date)
    return don, recu
