from django.db import models
from django.urls import reverse

from apps.comptes.models import Paroisse


class Famille(models.Model):
    nom = models.CharField("nom de famille", max_length=200)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="familles", on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "famille"
        verbose_name_plural = "familles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("paroissiens:famille_detail", args=[self.pk])


class Paroissien(models.Model):
    SEXE_CHOICES = [
        ("M", "Masculin"),
        ("F", "Féminin"),
    ]

    nom = models.CharField("nom", max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    sexe = models.CharField("sexe", max_length=1, choices=SEXE_CHOICES)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    photo = models.ImageField("photo", upload_to="paroissiens/", blank=True, null=True)
    famille = models.ForeignKey(
        Famille,
        verbose_name="famille",
        related_name="membres",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="paroissiens", on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "paroissien"
        verbose_name_plural = "paroissiens"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def get_absolute_url(self):
        return reverse("paroissiens:paroissien_detail", args=[self.pk])
