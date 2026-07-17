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
    Curé peut aussi désactiver/réactiver un membre (jamais lui-même). Le
    Curé peut également **modifier un membre** (coordonnées + rôle,
    `comptes:equipe_modifier`) et **réinitialiser son mot de passe**
    (`comptes:equipe_reinitialiser_mot_de_passe`, nouveau mot de passe
    temporaire affiché une seule fois, même principe que l'invitation).
    Ces deux actions, comme la désactivation, sont bloquées sur son propre
    compte (redirection vers « Mon compte ») et scopées à sa paroisse
    (`get_object_or_404(..., paroisse=request.paroisse)` → 404 sur un
    membre d'une autre paroisse).
  - **Abonnement** (`comptes:abonnement`) : changer d'offre ou annuler/
    réactiver l'abonnement de la paroisse. Modèle `Abonnement`
    (`apps/comptes/models.py`), bien distinct des `Don`/`RecuFiscal` de
    l'app finances qui sont la comptabilité *interne* de la paroisse.
  - **Pied de page dynamique** (`templates/base_public.html`) : plus de
    nom de paroisse figé en dur. Priorité au contexte `paroisse` explicite
    de la vue (pages publiques par paroisse — annonces, `paroisse` posé
    dans `get_context_data`), puis à `request.paroisse` (posé par
    `ParoisseCouranteMiddleware` pour un utilisateur connecté), sinon
    seulement « ParoisseConnect. » — un visiteur anonyme ou le superadmin
    (`/plateforme/`, sans paroisse) ne voient jamais de nom de paroisse.
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
  - `Paroisse` a des champs d'adresse structurés — `ville`, `commune`,
    `quartier`, `avenue` — plutôt qu'un unique champ « adresse » (toujours
    présent, composé automatiquement des trois derniers à l'inscription).
  - `/api/geocoder-inverse/` (public, sans authentification — utilisé avant
    la création de tout compte) : géocodage **inverse** (coordonnées →
    avenue/quartier/commune/ville). Sur la page de souscription, une carte
    Leaflet cliquable remplit ces champs automatiquement, et les
    coordonnées sont enregistrées dès la création de la paroisse — pas
    besoin de repasser par « Localiser automatiquement » ensuite.
  - `/api/rechercher-adresse/` (public) : géocodage **direct** combinant
    les champs déjà saisis (avenue, quartier, commune, ville) en une seule
    requête Nominatim, pour aider à se repérer sur la carte sans deviner —
    utile quand plusieurs communes partagent le nom d'une avenue.
  - Nominatim renvoie des coordonnées avec bien plus de décimales que les 6
    chiffres après la virgule acceptés par `Paroisse.latitude`/`longitude`
    (`DecimalField(max_digits=9, decimal_places=6)`). Corrigé : la carte de
    souscription arrondit désormais `lat`/`lon` à 6 décimales dès qu'un
    marqueur est posé (clic sur la carte ou sur un résultat de recherche) ;
    `GeocoderParoisseView` (tableau de bord) fait de même avant
    l'enregistrement. Sans cet arrondi, la validation du formulaire échouait
    silencieusement (champs cachés, aucune erreur visible) et, côté API,
    l'enregistrement aurait levé une erreur PostgreSQL en production
    (« numeric field overflow »). Une erreur explicite s'affiche désormais
    si la validation échoue malgré tout.
- ✅ Console de supervision plateforme (hors plan initial) — `apps/plateforme`,
  espace `/plateforme/` réservé au superadmin d'instance (`is_superuser`) :
  - Liste de toutes les paroisses inscrites avec leurs statistiques
    (utilisateurs, paroissiens) et leur statut.
  - Fiche paroisse : suspendre/réactiver l'accès, statistiques détaillées
    (paroissiens, actes sacramentels, dons), liste de tous les comptes de
    la paroisse avec réinitialisation de mot de passe individuelle (pas
    d'hypothèse d'un Curé unique — plusieurs comptes peuvent porter ce rôle).
  - **Suppression définitive d'une paroisse** (`plateforme:paroisse_supprimer`,
    `apps/plateforme/services.py::supprimer_paroisse`) : distincte de la
    suspension (réversible) — celle-ci efface la paroisse et toutes ses
    données. Chaque FK vers `Paroisse` est `on_delete=PROTECT` (§1, contre
    les pertes accidentelles), donc un `paroisse.delete()` direct lèverait
    `ProtectedError` ; le service supprime explicitement chaque registre
    dans l'ordre qui respecte aussi les contraintes PROTECT internes (reçu
    fiscal avant son don, intention de messe avant sa célébration, actes
    sacramentels et dons avant les paroissiens qu'ils référencent, annonces
    avant les comptes auteurs), le tout dans une seule
    `transaction.atomic()`. Confirmation obligatoire en retapant le nom
    exact de la paroisse (`ParoisseSupprimerForm`) — dernier garde-fou avant
    une action irréversible.
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
- ✅ Page publique des communiqués (hors plan initial) — `/paroisses/<slug>/annonces/`,
  consultable **sans compte** :
  - `Paroisse.slug` : identifiant unique généré automatiquement depuis le
    nom (avec désambiguïsation en cas de collision), migré en 3 étapes
    sûres (ajout du champ, backfill des paroisses existantes, puis
    contrainte d'unicité) pour ne jamais casser une base déjà peuplée.
  - `Annonce.publique` (défaut `False`) : une annonce n'est visible sur la
    page publique que si le Secrétaire/Curé l'y a explicitement autorisée
    — les communiqués internes ne fuitent pas vers les visiteurs.
  - La page publique d'une paroisse suspendue renvoie 404, comme le reste
    de l'application.
  - Lien direct vers cette page affiché dans la liste interne des
    annonces et sur la fiche paroisse de `/plateforme/`, pour que
    l'équipe et le superadmin la retrouvent facilement.
- ✅ Limites réelles par offre (hors plan initial) — `Abonnement.LIMITES`
  (`apps/comptes/models.py`), source unique utilisée à la fois par la page
  tarifs (affichage) et par les vues (contrôle d'accès) :
  - **Essentiel** (15 $/mois) : Sacrements, Célébrations, Finances. Pas de
    Paroissiens ni Communication. Jusqu'à 3 utilisateurs en plus du Curé.
  - **Standard** (35 $/mois) : + Paroissiens (jusqu'à 2000 membres).
    Jusqu'à 7 utilisateurs en plus du Curé. Communication toujours exclue.
  - **Pro** (sur devis) : tout illimité + Communication (et donc la page
    publique des communiqués, qui en dépend). Renommée depuis « Diocèse »
    (`comptes/migrations/0009_alter_abonnement_offre.py`, avec migration de
    données pour les abonnements existants) — ce nom entrait en collision
    avec `Paroisse.diocese`, un concept sans rapport (le diocèse de
    rattachement de la paroisse), pas un palier d'abonnement.
  - `ModuleAutoriseMixin` (`apps/comptes/mixins.py`) bloque réellement les
    vues d'un module non inclus (redirection + message), pas seulement la
    navigation — appliqué à `paroissiens` et `communication`. Si une
    paroisse n'a pas encore d'`Abonnement` (fixture de test, compte créé
    hors du flux normal), l'accès reste ouvert : la restriction est une
    règle de facturation, pas une isolation de sécurité.
  - La limite de paroissiens et la limite d'utilisateurs sont vérifiées au
    moment de la création (`ParoissienCreateView`, `InvitationCreateView`),
    pas seulement affichées — testé en créant réellement 2000 paroissiens
    puis en vérifiant que le 2001ᵉ est refusé.
  - Downgrade automatique de la page publique : si l'offre d'une paroisse
    n'inclut plus `communication`, sa page `/paroisses/<slug>/annonces/`
    renvoie 404 elle aussi, cohérent avec « communication → page publique ».
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
