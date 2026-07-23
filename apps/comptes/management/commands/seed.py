import datetime

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.celebrations.models import Celebration, IntentionMesse
from apps.communication.models import Annonce
from apps.comptes.models import Abonnement, Paroisse, Utilisateur
from apps.finances.models import Depense, OffrandeMesse
from apps.finances.services import enregistrer_don_avec_recu
from apps.paroissiens.models import Famille, Paroissien
from apps.sacrements.models import Bapteme

# Identifiants stables : relancer la commande les recrée toujours à
# l'identique, même après un `rm db.sqlite3` + `migrate`.
COMPTES_DEMO = [
    ("admin", "admin1234", None, None),
    ("cure", "cure1234", "Curé", "Jean Mbala"),
    ("secretaire", "secretaire1234", "Secrétaire", "Marie Kalonji"),
    ("tresorier", "tresorier1234", "Trésorier", "Paul Tshisekedi"),
    ("lecteur", "lecteur1234", "Lecteur", "Anne Kabila"),
]


class Command(BaseCommand):
    help = (
        "Crée la paroisse Saint Raphaël, un compte par rôle (Curé, Secrétaire, "
        "Trésorier, Lecteur) plus un superadmin, et un jeu de données de "
        "démonstration réaliste. Peut être relancée sans risque (idempotente)."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        paroisse = self._creer_paroisse()
        self._creer_abonnement(paroisse)
        self._creer_comptes(paroisse)
        self._creer_donnees_demo(paroisse)

        self.stdout.write(self.style.SUCCESS("\nJeu de données de démonstration prêt.\n"))
        self.stdout.write("Comptes disponibles :")
        for username, mot_de_passe, role, _ in COMPTES_DEMO:
            libelle_role = role or "superadmin"
            self.stdout.write(f"  {username:12s} / {mot_de_passe:16s} ({libelle_role})")

    def _creer_paroisse(self):
        paroisse, _ = Paroisse.objects.update_or_create(
            nom="Saint Raphaël",
            defaults=dict(
                diocese="Kinshasa",
                adresse="Boulevard du 30 Juin, Golf, Gombe",
                ville="Kinshasa",
                commune="Gombe",
                quartier="Golf",
                avenue="Boulevard du 30 Juin",
                latitude=-4.325,
                longitude=15.322,
                telephone="+243 810 000 000",
                email="contact@saintraphael.example",
            ),
        )
        return paroisse

    def _creer_abonnement(self, paroisse):
        Abonnement.objects.update_or_create(
            paroisse=paroisse, defaults=dict(offre="standard", statut="actif")
        )

    def _creer_comptes(self, paroisse):
        for username, mot_de_passe, role, nom_complet in COMPTES_DEMO:
            if username == "admin":
                utilisateur, cree = Utilisateur.objects.get_or_create(
                    username=username, defaults=dict(is_superuser=True, is_staff=True)
                )
            else:
                prenom, _, nom = nom_complet.partition(" ")
                utilisateur, cree = Utilisateur.objects.get_or_create(
                    username=username,
                    defaults=dict(paroisse=paroisse, first_name=prenom, last_name=nom),
                )
                if not cree:
                    utilisateur.paroisse = paroisse
                    utilisateur.save(update_fields=["paroisse"])

            utilisateur.set_password(mot_de_passe)
            utilisateur.is_active = True
            utilisateur.save()

            if role:
                utilisateur.groups.set([Group.objects.get(name=role)])

    def _creer_donnees_demo(self, paroisse):
        famille, _ = Famille.objects.get_or_create(
            nom="Mbala", paroisse=paroisse, defaults=dict(adresse="Quartier Righini")
        )
        paroissien, _ = Paroissien.objects.get_or_create(
            nom="Mbala",
            prenom="Jean",
            paroisse=paroisse,
            defaults=dict(sexe="M", famille=famille),
        )

        if not Bapteme.objects.filter(paroissien=paroissien, paroisse=paroisse).exists():
            Bapteme.objects.create(
                paroissien=paroissien,
                date=datetime.date(2000, 1, 9),
                lieu="Église Saint Raphaël",
                celebrant="Abbé Kalonji",
                parrain="Pierre Tshisekedi",
                marraine="Anne Kabila",
                paroisse=paroisse,
            )

        celebration, _ = Celebration.objects.get_or_create(
            date=datetime.date.today() + datetime.timedelta(days=7),
            heure=datetime.time(9, 0),
            type_celebration="messe",
            paroisse=paroisse,
            defaults=dict(celebrant="Abbé Kalonji", lieu="Église Saint Raphaël"),
        )
        IntentionMesse.objects.get_or_create(
            demandeur="Famille Mbala",
            celebration=celebration,
            paroisse=paroisse,
            defaults=dict(intention="Action de grâce", montant_offrande=10, devise="USD"),
        )

        # Démo en deux devises (§ finances : un solde par devise). On garde le
        # jeu idempotent par devise : relancer `seed` complète les mouvements
        # manquants sans dupliquer ceux déjà présents.
        dons_demo = [
            (25000, "CDF", "offrande", "especes"),
            (50, "USD", "dime", "mobile_money"),
        ]
        for montant, devise, type_don, mode in dons_demo:
            if not paroisse.dons.filter(devise=devise).exists():
                enregistrer_don_avec_recu(
                    paroisse=paroisse,
                    montant=montant,
                    devise=devise,
                    date=datetime.date.today(),
                    type_don=type_don,
                    mode_paiement=mode,
                    paroissien=paroissien,
                )

        OffrandeMesse.objects.get_or_create(
            paroisse=paroisse,
            libelle="Quête messe dominicale",
            defaults=dict(
                montant=8000,
                devise="CDF",
                date=datetime.date.today(),
                mode_paiement="especes",
            ),
        )

        depenses_demo = [
            ("Facture d'électricité", 45000, "CDF", "charges", "virement"),
            ("Achat de cierges et hosties", 20, "USD", "liturgie", "especes"),
            ("Réparation de la toiture", 120, "USD", "entretien", "mobile_money"),
        ]
        for libelle, montant, devise, categorie, mode in depenses_demo:
            Depense.objects.get_or_create(
                paroisse=paroisse,
                libelle=libelle,
                defaults=dict(
                    montant=montant,
                    devise=devise,
                    date=datetime.date.today(),
                    categorie=categorie,
                    mode_paiement=mode,
                ),
            )

        cure = Utilisateur.objects.get(username="cure")
        Annonce.objects.get_or_create(
            titre="Kermesse paroissiale",
            paroisse=paroisse,
            defaults=dict(
                contenu="La kermesse annuelle aura lieu le mois prochain, "
                "après la messe dominicale.",
                date_publication=datetime.date.today(),
                auteur=cure,
            ),
        )
