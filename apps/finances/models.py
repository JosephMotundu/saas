from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.comptes.managers import creer_manager_paroisse
from apps.comptes.models import Paroisse
from apps.core.devises import (  # noqa: F401 (ré-export pour compatibilité)
    DEVISE_CHOICES,
    SYMBOLES_DEVISE,
    formater_montant,
)
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
    montant = models.DecimalField("montant", max_digits=12, decimal_places=2)
    devise = models.CharField(
        "devise", max_length=3, choices=DEVISE_CHOICES, default="CDF"
    )
    date = models.DateField("date")
    type_don = models.CharField("type", max_length=20, choices=TYPE_CHOICES)
    mode_paiement = models.CharField(
        "mode de paiement", max_length=20, choices=MODE_PAIEMENT_CHOICES
    )
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="dons", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "don"
        verbose_name_plural = "dons"
        ordering = ["-date"]

    def __str__(self):
        donateur = self.paroissien.nom_complet() if self.paroissien else "Don anonyme"
        return f"{donateur} — {self.montant_affiche()} ({self.get_type_don_display()})"

    def montant_affiche(self):
        return formater_montant(self.montant, self.devise)

    def get_absolute_url(self):
        return reverse("finances:don_detail", args=[self.pk])


class Depense(models.Model):
    CATEGORIE_CHOICES = [
        ("charges", "Charges (eau, électricité, loyer)"),
        ("entretien", "Entretien et travaux"),
        ("liturgie", "Liturgie et culte"),
        ("salaires", "Salaires et indemnités"),
        ("charite", "Charité et aumônes"),
        ("administration", "Administration"),
        ("autre", "Autre"),
    ]

    libelle = models.CharField("libellé", max_length=150)
    montant = models.DecimalField("montant", max_digits=12, decimal_places=2)
    devise = models.CharField(
        "devise", max_length=3, choices=DEVISE_CHOICES, default="CDF"
    )
    date = models.DateField("date")
    categorie = models.CharField("catégorie", max_length=20, choices=CATEGORIE_CHOICES)
    mode_paiement = models.CharField(
        "mode de paiement", max_length=20, choices=Don.MODE_PAIEMENT_CHOICES
    )
    beneficiaire = models.CharField(
        "bénéficiaire", max_length=150, blank=True,
        help_text="Fournisseur ou personne réglée (facultatif).",
    )
    paroisse = models.ForeignKey(
        Paroisse,
        verbose_name="paroisse",
        related_name="depenses",
        on_delete=models.PROTECT,
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "dépense"
        verbose_name_plural = "dépenses"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.libelle} — {self.montant_affiche()} ({self.get_categorie_display()})"

    def montant_affiche(self):
        return formater_montant(self.montant, self.devise)

    def get_absolute_url(self):
        return reverse("finances:depense_detail", args=[self.pk])


class OffrandeMesse(models.Model):
    """Quête d'une messe, enregistrée par le trésorier après comptage.
    Saisie libre (pas de lien obligatoire vers une célébration) : on note le
    montant compté, sa devise et la date. Comptée dans le solde au même titre
    que les dons."""

    libelle = models.CharField(
        "libellé", max_length=150, blank=True,
        help_text="Ex. « Quête messe dominicale ». Facultatif.",
    )
    montant = models.DecimalField("montant", max_digits=12, decimal_places=2)
    devise = models.CharField(
        "devise", max_length=3, choices=DEVISE_CHOICES, default="CDF"
    )
    date = models.DateField("date")
    mode_paiement = models.CharField(
        "mode de paiement", max_length=20, choices=Don.MODE_PAIEMENT_CHOICES, default="especes"
    )
    paroisse = models.ForeignKey(
        Paroisse,
        verbose_name="paroisse",
        related_name="offrandes_messe",
        on_delete=models.PROTECT,
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "offrande de messe"
        verbose_name_plural = "offrandes de messe"
        ordering = ["-date"]

    def __str__(self):
        intitule = self.libelle or "Offrande de messe"
        return f"{intitule} — {self.montant_affiche()}"

    def montant_affiche(self):
        return formater_montant(self.montant, self.devise)

    def get_absolute_url(self):
        return reverse("finances:offrande_detail", args=[self.pk])


class RecuFiscal(models.Model):
    don = models.OneToOneField(
        Don, verbose_name="don", related_name="recu_fiscal", on_delete=models.PROTECT
    )
    numero = models.CharField("numéro", max_length=30, editable=False, blank=True)
    date_emission = models.DateField("date d'émission", default=timezone.now)

    objects = creer_manager_paroisse("don__paroisse")

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
