from django.conf import settings
from django.contrib.auth.models import Group
from django.db import models
from django.urls import reverse

from apps.comptes.managers import creer_manager_paroisse
from apps.comptes.models import Paroisse


class Annonce(models.Model):
    titre = models.CharField("titre", max_length=200)
    contenu = models.TextField("contenu")
    date_publication = models.DateField("date de publication")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        related_name="annonces",
        on_delete=models.PROTECT,
    )
    groupe_cible = models.ForeignKey(
        Group,
        verbose_name="groupe cible",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Laisser vide pour une annonce visible de toute la paroisse.",
    )
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="annonces", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "annonce"
        verbose_name_plural = "annonces"
        ordering = ["-date_publication"]

    def __str__(self):
        return self.titre

    def get_absolute_url(self):
        return reverse("communication:annonce_detail", args=[self.pk])
