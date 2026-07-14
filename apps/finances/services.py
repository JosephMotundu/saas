"""Logique métier réutilisable pour les finances (voir §9 du brief : couche
services pour les opérations qui dépassent un simple modèle)."""

from django.db import transaction

from .models import Don, RecuFiscal


@transaction.atomic
def enregistrer_don_avec_recu(*, paroisse, montant, date, type_don, mode_paiement, paroissien=None):
    """Crée un Don et son RecuFiscal dans une même transaction : soit les
    deux existent, soit aucun (§14 du brief — opération critique)."""
    don = Don.objects.create(
        paroisse=paroisse,
        montant=montant,
        date=date,
        type_don=type_don,
        mode_paiement=mode_paiement,
        paroissien=paroissien,
    )
    recu = RecuFiscal.objects.create(don=don, date_emission=date)
    return don, recu
