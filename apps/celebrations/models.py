from django.db import models
from django.urls import reverse

from apps.comptes.managers import creer_manager_paroisse
from apps.comptes.models import Paroisse
from apps.core.devises import DEVISE_CHOICES, formater_montant


class Celebration(models.Model):
    TYPE_CHOICES = [
        ("messe", "Messe"),
        ("vigile", "Vigile"),
        ("fete", "Fête"),
        ("autre", "Autre"),
    ]

    date = models.DateField("date")
    heure = models.TimeField("heure")
    type_celebration = models.CharField("type", max_length=20, choices=TYPE_CHOICES)
    celebrant = models.CharField("célébrant", max_length=200)
    lieu = models.CharField("lieu", max_length=200, blank=True)
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="celebrations", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "célébration"
        verbose_name_plural = "célébrations"
        ordering = ["date", "heure"]

    def __str__(self):
        return f"{self.get_type_celebration_display()} du {self.date} à {self.heure}"

    def get_absolute_url(self):
        return reverse("celebrations:celebration_detail", args=[self.pk])


class IntentionMesse(models.Model):
    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("celebree", "Célébrée"),
        ("annulee", "Annulée"),
    ]

    demandeur = models.CharField("demandeur", max_length=200)
    intention = models.CharField("intention", max_length=300)
    montant_offrande = models.DecimalField(
        "montant de l'offrande", max_digits=12, decimal_places=2, null=True, blank=True
    )
    devise = models.CharField(
        "devise", max_length=3, choices=DEVISE_CHOICES, default="CDF"
    )
    statut = models.CharField(
        "statut", max_length=20, choices=STATUT_CHOICES, default="en_attente"
    )
    celebration = models.ForeignKey(
        Celebration,
        verbose_name="célébration",
        related_name="intentions",
        on_delete=models.PROTECT,
    )
    paroisse = models.ForeignKey(Paroisse, verbose_name="paroisse", on_delete=models.PROTECT)

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "intention de messe"
        verbose_name_plural = "intentions de messe"
        ordering = ["-celebration__date"]

    def __str__(self):
        return f"{self.demandeur} — {self.intention}"

    def offrande_affichee(self):
        """Montant de l'offrande avec sa devise, ou « — » si non renseigné."""
        if self.montant_offrande is None:
            return "—"
        return formater_montant(self.montant_offrande, self.devise)

    def get_absolute_url(self):
        return reverse("celebrations:intention_detail", args=[self.pk])
