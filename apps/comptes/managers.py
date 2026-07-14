"""Manager/QuerySet multi-tenant par défaut (§4 du brief).

`creer_manager_paroisse()` fabrique un manager dont `get_queryset()` filtre
automatiquement sur la paroisse courante (posée par ParoisseCouranteMiddleware
dans une ContextVar). C'est le filet de sécurité qui protège aussi le Django
Admin — `ModelAdmin.get_queryset()` utilise le manager par défaut du modèle.

Comportement hors requête (aucune paroisse courante définie — migrations,
shell, commandes de gestion, tests unitaires appelant les modèles
directement) : aucun filtrage n'est appliqué, pour ne pas gêner ces usages
légitimes. Un superadmin (paroisse=None) n'est, de la même façon, jamais
filtré : il gère plusieurs paroisses par conception (§1 du brief).

Les vues continuent par ailleurs de filtrer explicitement par paroisse
(apps.comptes.mixins.FiltrageParoisseMixin) : ce manager est une défense en
profondeur, pas un remplacement de cette vérification explicite.
"""

from django.db import models

from .contexte import obtenir_paroisse_courante


def creer_manager_paroisse(champ_paroisse="paroisse"):
    class ParoisseQuerySet(models.QuerySet):
        def de_la_paroisse_courante(self):
            paroisse = obtenir_paroisse_courante()
            if paroisse is None:
                return self
            return self.filter(**{champ_paroisse: paroisse})

    class ParoisseManager(models.Manager.from_queryset(ParoisseQuerySet)):
        def get_queryset(self):
            return super().get_queryset().de_la_paroisse_courante()

    return ParoisseManager()
