"""Logique métier réutilisable pour la plateforme (voir §9 du brief : couche
services pour les opérations qui dépassent un simple modèle)."""

from django.db import transaction

from apps.celebrations.models import Celebration, IntentionMesse
from apps.comptes.models import Utilisateur
from apps.communication.models import Annonce
from apps.finances.models import Don, RecuFiscal
from apps.paroissiens.models import Famille, Paroissien
from apps.sacrements.models import Bapteme, Communion, Confirmation, Funerailles, Mariage


@transaction.atomic
def supprimer_paroisse(paroisse):
    """Supprime une paroisse et toutes ses données (§4 : le tenant). Réservé
    au superadmin de la plateforme (voir plateforme.views.ParoisseSupprimerView).

    Chaque FK vers Paroisse est volontairement `on_delete=PROTECT` (§1 :
    contrainte d'intégrité contre les fuites/pertes accidentelles) — un
    `paroisse.delete()` direct échouerait donc avec `ProtectedError`. Cette
    fonction supprime explicitement chaque registre dans l'ordre qui respecte
    les autres contraintes PROTECT internes (ex. un reçu fiscal avant son don,
    une intention de messe avant sa célébration), le tout dans une seule
    transaction : soit la paroisse disparaît entièrement, soit rien ne
    change.
    """
    RecuFiscal.objects.filter(don__paroisse=paroisse).delete()
    Don.objects.filter(paroisse=paroisse).delete()
    IntentionMesse.objects.filter(paroisse=paroisse).delete()
    Celebration.objects.filter(paroisse=paroisse).delete()
    for modele in (Bapteme, Communion, Confirmation, Funerailles, Mariage):
        modele.objects.filter(paroisse=paroisse).delete()
    Annonce.objects.filter(paroisse=paroisse).delete()
    Paroissien.objects.filter(paroisse=paroisse).delete()
    Famille.objects.filter(paroisse=paroisse).delete()
    Utilisateur.objects.filter(paroisse=paroisse).delete()
    paroisse.delete()
