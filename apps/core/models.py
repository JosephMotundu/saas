from django.db import models


class ContenuVitrine(models.Model):
    """Contenu éditable de la section « hero » de la page d'accueil
    publique — gardé volontairement minimal (le message publicitaire
    principal, pas tout le site) et éditable depuis /plateforme/ par le
    superadmin. Singleton : une seule ligne, chargée via `charger()`."""

    titre_hero = models.CharField(
        "titre principal",
        max_length=200,
        default=(
            "Le registre de votre paroisse, tenu avec la même rigueur "
            "qu'un missel relié"
        ),
    )
    accroche_hero = models.TextField(
        "accroche",
        default=(
            "ParoisseConnect rassemble paroissiens, sacrements, célébrations "
            "et dons dans un seul registre numérique, pensé pour un "
            "secrétariat paroissial — pas pour un tableau de bord marketing."
        ),
    )
    image_hero = models.ImageField("image", upload_to="vitrine/", blank=True, null=True)
    titre_cta = models.CharField(
        "titre de l'appel à l'action", max_length=200, default="Prêt pour votre paroisse ?"
    )
    texte_cta = models.CharField(
        "texte de l'appel à l'action",
        max_length=300,
        default="Créez votre espace ParoisseConnect en quelques minutes, sans engagement.",
    )

    class Meta:
        verbose_name = "contenu de la vitrine"
        verbose_name_plural = "contenu de la vitrine"

    def __str__(self):
        return "Contenu de la page d'accueil"

    @classmethod
    def charger(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
