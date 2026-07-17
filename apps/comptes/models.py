from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Paroisse(models.Model):
    """Le tenant : chaque paroisse cliente de l'instance ParoisseConnect."""

    nom = models.CharField("nom", max_length=200, unique=True)
    slug = models.SlugField(
        "identifiant public",
        max_length=220,
        unique=True,
        blank=True,
        help_text="Généré automatiquement depuis le nom ; utilisé dans l'URL de la "
        "page publique de la paroisse (communiqués visibles sans compte).",
    )
    diocese = models.CharField("diocèse", max_length=200)
    adresse = models.CharField(
        "adresse",
        max_length=255,
        help_text="Composée automatiquement à l'inscription à partir de l'avenue, "
        "du quartier et de la commune ; modifiable librement ensuite.",
    )
    ville = models.CharField("ville", max_length=100)
    commune = models.CharField("commune", max_length=100, blank=True)
    quartier = models.CharField("quartier", max_length=100, blank=True)
    avenue = models.CharField("avenue", max_length=200, blank=True)
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

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nom) or "paroisse"
            slug = base
            compteur = 1
            while Paroisse.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                compteur += 1
                slug = f"{base}-{compteur}"
            self.slug = slug
        super().save(*args, **kwargs)


class Abonnement(models.Model):
    """L'abonnement SaaS d'une paroisse — à ne pas confondre avec les `Don`/
    `RecuFiscal` de l'app finances, qui sont la comptabilité *interne* de la
    paroisse. Ceci est la facturation de l'instance ParoisseConnect elle-même.
    """

    OFFRE_CHOICES = [
        ("essentiel", "Essentiel"),
        ("standard", "Standard"),
        ("pro", "Pro"),
    ]

    STATUT_CHOICES = [
        ("actif", "Actif"),
        ("annule", "Annulé"),
    ]

    # Ce que chaque offre inclut réellement — source unique utilisée à la
    # fois par la page tarifs (affichage) et par les vues (contrôle
    # d'accès réel, pas seulement du texte marketing). `max_*=None`
    # signifie « illimité ».
    LIMITES = {
        "essentiel": {
            "prix_affiche": "15 $ / mois",
            "max_utilisateurs_supplementaires": 3,
            "max_paroissiens": None,
            "modules": frozenset({"sacrements", "celebrations", "finances"}),
        },
        "standard": {
            "prix_affiche": "35 $ / mois",
            "max_utilisateurs_supplementaires": 7,
            "max_paroissiens": 2000,
            "modules": frozenset({"sacrements", "celebrations", "finances", "paroissiens"}),
        },
        "pro": {
            "prix_affiche": "Sur devis",
            "max_utilisateurs_supplementaires": None,
            "max_paroissiens": None,
            "modules": frozenset(
                {"sacrements", "celebrations", "finances", "paroissiens", "communication"}
            ),
        },
    }

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

    def limites(self):
        return self.LIMITES[self.offre]

    def module_autorise(self, nom_module):
        return nom_module in self.limites()["modules"]

    def max_utilisateurs_supplementaires(self):
        return self.limites()["max_utilisateurs_supplementaires"]

    def max_paroissiens(self):
        return self.limites()["max_paroissiens"]

    def prix_affiche(self):
        return self.limites()["prix_affiche"]


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
