# ParoisseConnect

SaaS de gestion paroissiale (multi-tenant) — projet de fin d'études L4 Génie
Logiciel, UPC/FASI. Instance de démonstration : paroisse Saint Raphaël.

## Stack

Django 5 / DRF / PostgreSQL / Bootstrap 5 (templates server-rendered) /
Leaflet + Nominatim / JWT + 2FA TOTP / Docker.

## Démarrage avec Docker (recommandé)

```bash
cp .env.example .env   # ajuster les valeurs si besoin
make build
make up
make migrate
make seed               # paroisse Saint Raphaël + jeu de données de démo
make createsuperuser
```

L'application est disponible sur http://localhost:8000.

## Démarrage en local sans Docker (SQLite)

Nécessite **Python 3.12** (Django 5 n'est pas compatible avec des versions plus
récentes de Python, ex. 3.14, sous le client de test Django).

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
# éditer .env : DATABASE_URL=sqlite:///db.sqlite3
python manage.py migrate
python manage.py runserver
```

## Tests

```bash
make test
# ou en local :
pytest
```

## Structure

```
config/           réglages Django (settings/base.py, dev.py, prod.py), urls, wsgi
apps/             applications métier (comptes, paroissiens, sacrements, ...)
templates/        gabarits partagés
static/           assets front (CSS custom surchargeant Bootstrap 5)
requirements/     dépendances (base / dev / prod)
```

## Architecture multi-tenant

1. `ParoisseCouranteMiddleware` (`apps/comptes/middleware.py`) détermine la
   paroisse de l'utilisateur connecté à chaque requête et l'expose sur
   `request.paroisse`.
2. Il alimente aussi une `ContextVar` (`apps/comptes/contexte.py`), lue par
   `creer_manager_paroisse()` (`apps/comptes/managers.py`) : le manager par
   défaut (`objects`) de chaque modèle métier (paroissiens, sacrements,
   célébrations, finances, communication) filtre donc **automatiquement**
   sur la paroisse courante, y compris dans le Django Admin (qui utilise ce
   même manager par défaut).
3. Un superadmin (`paroisse=None`) n'est jamais filtré : il gère plusieurs
   paroisses par conception.
4. Hors requête (migrations, shell, commandes, tests unitaires appelant les
   modèles directement), aucune paroisse courante n'est définie : le manager
   ne filtre rien, pour ne pas gêner ces usages légitimes.
5. Les vues ajoutent un filtrage explicite (`FiltrageParoisseMixin`) en plus
   du manager : défense en profondeur, pas le seul rempart.
6. `Paroisse` et `Utilisateur` n'ont volontairement pas ce manager auto-
   filtrant (`Paroisse` EST le tenant ; `Utilisateur` est consulté pendant
   l'authentification, avant qu'une paroisse courante ne soit connue) — leur
   isolation dans l'admin est donc explicite, voir `apps/comptes/admin.py`.

## État d'avancement

Le projet est construit par étapes (voir brief).

- ✅ Étape 1 — scaffolding (settings dev/prod, Docker, PostgreSQL, Git)
- ✅ Étape 2 — app `comptes` : modèles `Paroisse`/`Utilisateur`, groupes de
  rôles (Curé, Secrétaire, Trésorier, Lecteur), connexion/déconnexion, admin
- ✅ Fondations des templates — `theme.css` (design tokens + surcharge
  Bootstrap), `base.html`/`base_public.html`/`base_app.html`, app `core`
  (vitrine publique : accueil, fonctionnalités, tarifs ; tableau de bord
  avec carte Leaflet et compteurs)
- ✅ Étape 4 — app `paroissiens` : `Famille`/`Paroissien`, CRUD complet
- ✅ Étape 5 — app `sacrements` : Baptême/Communion/Confirmation/Mariage/
  Funérailles, numérotation d'acte par paroisse, mentions marginales,
  certificats imprimables
- ✅ Étape 6 — app `celebrations` : célébrations et intentions de messe
- ✅ Étape 7 — app `finances` : dons et reçus fiscaux (création atomique)
- ✅ Étape 8 — app `communication` : annonces paroissiales
- ✅ Étape 3 — middleware et managers multi-tenant : `ParoisseCouranteMiddleware`
  expose `request.paroisse` et alimente une ContextVar lue par un manager par
  défaut appliqué à tous les modèles métier, qui filtre automatiquement sur
  la paroisse courante (y compris dans le Django Admin). `Paroisse` et
  `Utilisateur` sont isolés explicitement dans leurs `ModelAdmin` (raisons
  détaillées dans `apps/comptes/managers.py` et `apps/comptes/admin.py`).
- ✅ Conventions SaaS (hors plan initial, avant les étapes 9-11) :
  - **Inscription self-service** (`/souscription/`) : crée réellement la
    `Paroisse`, son `Abonnement` et le compte du premier Curé (transaction
    atomique), puis connecte directement l'utilisateur. Remplace l'ancienne
    page de démonstration qui ne persistait rien.
  - **Mon compte** (`comptes:profil`) : modifier son profil, changer son
    mot de passe (vues Django standard, gabarits ré-habillés).
  - **Équipe** (`comptes:equipe`) : le Curé invite un collaborateur
    (Secrétaire/Trésorier/Lecteur/Curé) — mot de passe temporaire généré
    côté serveur, jamais choisi par l'inviteur, affiché une seule fois ; le
    Curé peut aussi désactiver/réactiver un membre (jamais lui-même).
  - **Abonnement** (`comptes:abonnement`) : changer d'offre ou annuler/
    réactiver l'abonnement de la paroisse. Modèle `Abonnement`
    (`apps/comptes/models.py`), bien distinct des `Don`/`RecuFiscal` de
    l'app finances qui sont la comptabilité *interne* de la paroisse.
- ⏳ Étape 9 — API DRF + JWT + géocodage Nominatim
- ⏳ Étape 10 — 2FA TOTP
- ⏳ Étape 11 — Admin complet pour toutes les entités, commandes `seed`/`backup`

## Rôles et accès aux modules

| Module | Curé | Secrétaire | Trésorier | Lecteur |
|---|---|---|---|---|
| Paroissiens / Familles | lecture + écriture | lecture + écriture | — | lecture |
| Sacrements | lecture + écriture | lecture + écriture | — | lecture |
| Célébrations / Intentions | lecture + écriture | lecture + écriture | — | lecture |
| Finances (dons/reçus) | lecture + écriture | — | lecture + écriture | lecture |
| Communication (annonces) | lecture + écriture | lecture + écriture | — | lecture |

Les registres sacramentels et les dons/reçus ne sont jamais supprimables
(seulement modifiables) : ce sont des pièces canoniques ou fiscales, pas du
contenu éditorial. Seules les annonces peuvent être supprimées.
