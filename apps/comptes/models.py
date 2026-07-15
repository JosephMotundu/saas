from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


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
    est_active = models.BooleanField(
        "active",
        default=True,
        help_text=(
            "Décoché : la paroisse est suspendue par la plateforme (distinct de "
            "l'abonnement, que le Curé gère lui-même). Personne ne peut plus s'y "
            "connecter tant qu'elle n'est pas réactivée."
        ),
    )

    class Meta:
        verbose_name = "paroisse"
        verbose_name_plural = "paroisses"
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Abonnement(models.Model):
    """L'abonnement SaaS d'une paroisse — à ne pas confondre avec les `Don`/
    `RecuFiscal` de l'app finances, qui sont la comptabilité *interne* de la
    paroisse. Ceci est la facturation de l'instance ParoisseConnect elle-même.
    """

    OFFRE_CHOICES = [
        ("essentiel", "Essentiel"),
        ("standard", "Standard"),
        ("diocese", "Diocèse"),
    ]

    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("annule", "Annulé"),
    ]

    paroisse = models.OneToOneField(
        Paroisse, verbose_name="paroisse", related_name="abonnement", on_delete=models.CASCADE
    )
    offre = models.CharField("offre", max_length=20, choices=OFFRE_CHOICES)
    statut = models.CharField(
        "statut", max_length=20, choices=STATUT_CHOICES, default="actif"
    )
    date_debut = models.DateField("date de début", auto_now_add=True)
    date_annulation = models.DateField("date d'annulation", null=True, blank=True)

    class Meta:
        verbose_name = "abonnement"
        verbose_name_plural = "abonnements"

    def __str__(self):
        return f"{self.paroisse.nom} — {self.get_offre_display()} ({self.get_statut_display()})"

    def annuler(self):
        self.statut = "annule"
        self.date_annulation = timezone.now().date()
        self.save(update_fields=["statut", "date_annulation"])

    def reactiver(self):
        self.statut = "actif"
        self.date_annulation = None
        self.save(update_fields=["statut", "date_annulation"])


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
