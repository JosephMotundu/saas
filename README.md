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
make seed               # paroisse Saint Raphaël + un compte par rôle + données de démo
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
python manage.py seed
python manage.py runserver
```

## Comptes de démonstration

`python manage.py seed` (ou `make seed`) crée — ou recrée à l'identique,
la commande est idempotente — la paroisse Saint Raphaël et ces comptes :

| Utilisateur | Mot de passe | Rôle |
|---|---|---|
| `admin` | `admin1234` | Superadministrateur (accès à toutes les paroisses) |
| `cure` | `cure1234` | Curé |
| `secretaire` | `secretaire1234` | Secrétaire |
| `tresorier` | `tresorier1234` | Trésorier |
| `lecteur` | `lecteur1234` | Lecteur |

**En cas d'erreur du type « no such table » / « aucune table de ce type »** :
la base SQLite locale (`db.sqlite3`, volontairement absente du dépôt) n'a
pas été migrée. Il suffit de relancer :

```bash
python manage.py migrate
python manage.py seed
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
- ✅ Commande `manage.py seed` (`apps/comptes/management/commands/seed.py`) —
  idempotente : paroisse Saint Raphaël, abonnement, un compte par rôle,
  jeu de données de démonstration (famille, paroissien, baptême,
  célébration + intention, don + reçu, annonce). Le reste de l'étape 11
  (commande `backup`, admin complet — déjà largement fait au fil des
  apps) reste à finir.
- ✅ Étape 9 — API DRF + JWT + géocodage Nominatim (`apps/api`) :
  - Endpoints REST pour paroissiens, célébrations, intentions de messe,
    dons, annonces — lecture/écriture selon le rôle (`creer_permission_role`,
    équivalent DRF de `RoleRequisMixin`).
  - Authentification JWT (`/api/jeton/`, `/api/jeton/rafraichir/`) en plus
    de la session (utile pour que le tableau de bord appelle l'API sans
    jeton séparé).
  - Isolation multi-tenant explicite par ViewSet (`IsolationParoisseMixin`)
    plutôt que de dépendre du manager automatique : l'authentification JWT
    a lieu *après* `ParoisseCouranteMiddleware` dans le cycle de requête,
    donc la ContextVar n'est pas fiable pour les appels au jeton seul.
  - Créer un don via l'API passe par `services.enregistrer_don_avec_recu` :
    même garantie de transaction atomique que depuis l'interface web.
  - `/api/paroisse/geocoder/` (Curé uniquement) consomme l'API Nominatim
    pour géocoder l'adresse de la paroisse ; bouton « Localiser
    automatiquement » sur le tableau de bord, qui recharge ensuite la
    carte Leaflet avec les coordonnées obtenues.
- ✅ Console de supervision plateforme (hors plan initial) — `apps/plateforme`,
  espace `/plateforme/` réservé au superadmin d'instance (`is_superuser`) :
  - Liste de toutes les paroisses inscrites avec leurs statistiques
    (utilisateurs, paroissiens) et leur statut.
  - Fiche paroisse : suspendre/réactiver l'accès, statistiques détaillées
    (paroissiens, actes sacramentels, dons), liste de tous les comptes de
    la paroisse avec réinitialisation de mot de passe individuelle (pas
    d'hypothèse d'un Curé unique — plusieurs comptes peuvent porter ce rôle).
  - `Paroisse.est_active` est **distinct** de `Abonnement.statut` : la
    suspension est une décision de la plateforme, l'annulation d'abonnement
    une décision du Curé — les confondre aurait permis à une paroisse
    suspendue de se « réactiver » elle-même.
  - La suspension bloque la connexion (`ConnexionForm.confirm_login_allowed`),
    coupe immédiatement une session déjà ouverte (`ParoisseCouranteMiddleware`),
    et empêche l'émission ou l'usage d'un jeton JWT.
  - Édition du contenu « hero » de la page d'accueil publique
    (`ContenuVitrine`, app `core`) — titre, accroche, image, appel à
    l'action ; scope volontairement limité à cette section, pas un CMS
    complet.
  - Un superadmin qui se connecte est redirigé vers `/plateforme/` plutôt
    que vers un tableau de bord vide (il n'appartient à aucune paroisse).
- ⏳ Étape 10 — 2FA TOTP

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
