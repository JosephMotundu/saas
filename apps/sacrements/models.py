from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.comptes.models import Paroisse
from apps.paroissiens.models import Paroissien


class ActeBase(models.Model):
    """Champs communs à tous les actes sacramentels : un registre relié,
    numéroté, jamais anonyme sur la paroisse qui l'a enregistré.

    Le numéro d'acte n'est unique que par paroisse (chaque registre
    paroissial a sa propre numérotation) — la contrainte d'unicité
    correspondante est déclarée sur chaque modèle concret, voir Meta.
    """

    PREFIXE = "ACT"

    numero_acte = models.CharField(
        "numéro d'acte", max_length=30, editable=False, blank=True
    )
    date = models.DateField("date")
    lieu = models.CharField("lieu", max_length=200, blank=True)
    celebrant = models.CharField("célébrant", max_length=200)
    paroisse = models.ForeignKey(Paroisse, verbose_name="paroisse", on_delete=models.PROTECT)
    date_enregistrement = models.DateTimeField("date d'enregistrement", auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-date"]

    def generer_numero_acte(self):
        annee = self.date.year if self.date else timezone.now().year
        compte = (
            type(self)
            .objects.filter(paroisse=self.paroisse, date__year=annee)
            .exclude(pk=self.pk)
            .count()
            + 1
        )
        return f"{self.PREFIXE}-{annee}-{compte:04d}"

    def save(self, *args, **kwargs):
        if not self.numero_acte:
            self.numero_acte = self.generer_numero_acte()
        super().save(*args, **kwargs)


class ActePersonnel(ActeBase):
    paroissien = models.ForeignKey(
        Paroissien, verbose_name="paroissien", on_delete=models.PROTECT
    )

    class Meta(ActeBase.Meta):
        abstract = True

    def __str__(self):
        return f"{self.numero_acte} — {self.paroissien.nom_complet()}"


class Bapteme(ActePersonnel):
    PREFIXE = "BAP"

    parrain = models.CharField("parrain", max_length=200, blank=True)
    marraine = models.CharField("marraine", max_length=200, blank=True)

    class Meta:
        verbose_name = "baptême"
        verbose_name_plural = "baptêmes"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["paroisse", "numero_acte"], name="unique_numero_acte_bapteme"
            )
        ]

    def get_absolute_url(self):
        return reverse("sacrements:bapteme_detail", args=[self.pk])


class Communion(ActePersonnel):
    PREFIXE = "COM"

    class Meta:
        verbose_name = "communion"
        verbose_name_plural = "communions"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["paroisse", "numero_acte"], name="unique_numero_acte_communion"
            )
        ]

    def get_absolute_url(self):
        return reverse("sacrements:communion_detail", args=[self.pk])


class Confirmation(ActePersonnel):
    PREFIXE = "CONF"

    class Meta:
        verbose_name = "confirmation"
        verbose_name_plural = "confirmations"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["paroisse", "numero_acte"], name="unique_numero_acte_confirmation"
            )
        ]

    def get_absolute_url(self):
        return reverse("sacrements:confirmation_detail", args=[self.pk])


class Funerailles(ActePersonnel):
    PREFIXE = "FUN"

    class Meta:
        verbose_name = "funérailles"
        verbose_name_plural = "funérailles"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["paroisse", "numero_acte"], name="unique_numero_acte_funerailles"
            )
        ]

    def get_absolute_url(self):
        return reverse("sacrements:funerailles_detail", args=[self.pk])


class Mariage(ActeBase):
    PREFIXE = "MAR"

    conjoint1 = models.ForeignKey(
        Paroissien,
        verbose_name="premier conjoint",
        on_delete=models.PROTECT,
        related_name="mariages_conjoint1",
    )
    conjoint2 = models.ForeignKey(
        Paroissien,
        verbose_name="second conjoint",
        on_delete=models.PROTECT,
        related_name="mariages_conjoint2",
    )
    temoins = models.CharField("témoins", max_length=300, blank=True)

    class Meta:
        verbose_name = "mariage"
        verbose_name_plural = "mariages"
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["paroisse", "numero_acte"], name="unique_numero_acte_mariage"
            )
        ]

    def __str__(self):
        return f"{self.numero_acte} — {self.conjoint1.nom_complet()} & {self.conjoint2.nom_complet()}"

    def get_absolute_url(self):
        return reverse("sacrements:mariage_detail", args=[self.pk])


class MentionMarginale(models.Model):
    TYPE_CHOICES = [
        ("mariage", "Mariage"),
        ("ordination", "Ordination"),
        ("deces", "Décès"),
        ("autre", "Autre"),
    ]

    bapteme = models.ForeignKey(
        Bapteme,
        verbose_name="baptême",
        related_name="mentions_marginales",
        on_delete=models.CASCADE,
    )
    type_mention = models.CharField("type", max_length=20, choices=TYPE_CHOICES)
    date = models.DateField("date")
    reference = models.CharField("référence", max_length=200, blank=True)
    paroisse = models.ForeignKey(Paroisse, verbose_name="paroisse", on_delete=models.PROTECT)

    class Meta:
        verbose_name = "mention marginale"
        verbose_name_plural = "mentions marginales"
        ordering = ["date"]

    def __str__(self):
        return f"{self.get_type_mention_display()} — {self.bapteme}"
