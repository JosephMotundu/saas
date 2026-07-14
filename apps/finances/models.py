from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.comptes.models import Paroisse
from apps.paroissiens.models import Paroissien


class Don(models.Model):
    TYPE_CHOICES = [
        ("dime", "Dîme"),
        ("offrande", "Offrande"),
        ("quete", "Quête"),
        ("autre", "Autre"),
    ]

    MODE_PAIEMENT_CHOICES = [
        ("especes", "Espèces"),
        ("mobile_money", "Mobile money"),
        ("virement", "Virement"),
        ("cheque", "Chèque"),
    ]

    paroissien = models.ForeignKey(
        Paroissien,
        verbose_name="donateur",
        related_name="dons",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Laisser vide pour un don anonyme.",
    )
    montant = models.DecimalField("montant", max_digits=10, decimal_places=2)
    date = models.DateField("date")
    type_don = models.CharField("type", max_length=20, choices=TYPE_CHOICES)
    mode_paiement = models.CharField(
        "mode de paiement", max_length=20, choices=MODE_PAIEMENT_CHOICES
    )
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="dons", on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "don"
        verbose_name_plural = "dons"
        ordering = ["-date"]

    def __str__(self):
        donateur = self.paroissien.nom_complet() if self.paroissien else "Don anonyme"
        return f"{donateur} — {self.montant} ({self.get_type_don_display()})"

    def get_absolute_url(self):
        return reverse("finances:don_detail", args=[self.pk])


class RecuFiscal(models.Model):
    don = models.OneToOneField(
        Don, verbose_name="don", related_name="recu_fiscal", on_delete=models.PROTECT
    )
    numero = models.CharField("numéro", max_length=30, editable=False, blank=True)
    date_emission = models.DateField("date d'émission", default=timezone.now)

    class Meta:
        verbose_name = "reçu fiscal"
        verbose_name_plural = "reçus fiscaux"
        ordering = ["-date_emission"]
        constraints = [
            models.UniqueConstraint(
                fields=["don"], name="unique_recu_fiscal_par_don"
            )
        ]

    def __str__(self):
        return self.numero

    def generer_numero(self):
        paroisse = self.don.paroisse
        annee = self.date_emission.year
        compte = (
            RecuFiscal.objects.filter(don__paroisse=paroisse, date_emission__year=annee)
            .exclude(pk=self.pk)
            .count()
            + 1
        )
        return f"REC-{annee}-{compte:04d}"

    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generer_numero()
        super().save(*args, **kwargs)
