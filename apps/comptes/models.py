from django.contrib.auth.models import AbstractUser
from django.db import models


class Paroisse(models.Model):
    """Le tenant : chaque paroisse cliente de l'instance ParoisseConnect."""

    nom = models.CharField("nom", max_length=200, unique=True)
    diocese = models.CharField("diocèse", max_length=200)
    adresse = models.CharField("adresse", max_length=255)
    ville = models.CharField("ville", max_length=100)
    latitude = models.DecimalField(
        "latitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        "longitude", max_digits=9, decimal_places=6, null=True, blank=True
    )
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    date_creation = models.DateTimeField("date de création", auto_now_add=True)

    class Meta:
        verbose_name = "paroisse"
        verbose_name_plural = "paroisses"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Utilisateur(AbstractUser):
    """Utilisateur applicatif. Rattaché à une paroisse, sauf le superadmin
    d'instance (paroisse=None) qui administre plusieurs paroisses."""

    paroisse = models.ForeignKey(
        Paroisse,
        verbose_name="paroisse",
        related_name="utilisateurs",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Laisser vide pour un compte d'administration d'instance (superadmin).",
    )

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.get_full_name() or self.username
