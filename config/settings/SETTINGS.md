# Documentation des réglages (`config/settings/`)

Ce dossier contient la configuration Django de ParoisseConnect. Elle est
**découpée par environnement** (patron « split settings ») plutôt que réunie
dans un unique `settings.py` : les réglages communs vivent dans `base.py`, et
chaque environnement (`dev.py`, `prod.py`) l'importe puis n'y ajoute que ses
différences. On ne modifie jamais de valeur sensible en dur : les secrets et
les réglages qui changent d'une machine à l'autre viennent des **variables
d'environnement** (fichier `.env`, voir `.env.example`).

## Vue d'ensemble des fichiers

| Fichier         | Rôle                                                                 |
|-----------------|----------------------------------------------------------------------|
| `__init__.py`   | Fichier vide : fait de `settings/` un package Python importable.      |
| `base.py`       | Tous les réglages communs à tous les environnements.                 |
| `dev.py`        | Surcharges pour le développement local (`base` + `DEBUG=True`).      |
| `prod.py`       | Surcharges pour la production (HTTPS, sécurité, e-mail SMTP…).        |
| `SETTINGS.md`   | Ce document.                                                          |

## Comment Django choisit le bon fichier

Django lit la variable d'environnement `DJANGO_SETTINGS_MODULE`. Selon le
contexte, la valeur par défaut est déjà posée :

| Contexte d'exécution        | Valeur utilisée            | Défini dans            |
|-----------------------------|----------------------------|------------------------|
| `python manage.py …` (local)| `config.settings.dev`      | `manage.py`            |
| Tests (`pytest`)            | `config.settings.dev`      | `pytest.ini`           |
| `docker-compose up`         | `config.settings.dev`      | `docker-compose.yml`   |
| Serveur WSGI (déploiement)  | `config.settings.prod`     | `config/wsgi.py`       |
| Serveur ASGI (déploiement)  | `config.settings.prod`     | `config/asgi.py`       |

On peut toujours forcer un autre module : `DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check`.

---

## `base.py` — réglages communs

Point d'entrée de tous les autres fichiers. Détail par bloc :

### Chargement de l'environnement (lignes 6-20)
- `BASE_DIR` : racine du projet (trois niveaux au-dessus de ce fichier).
- `environ.Env(...)` + `read_env(BASE_DIR / ".env")` : lit le fichier `.env` et
  expose ses clés via `env(...)`. La librairie `django-environ` convertit les
  types (`env.bool`, `env.list`, `env.db`, `env.int`).
- `SECRET_KEY` : clé de signature Django, **obligatoirement** fournie via
  `DJANGO_SECRET_KEY` en production (la valeur par défaut n'est là que pour le
  dev).
- `DEBUG` : `False` par défaut ; réactivé dans `dev.py`.
- `ALLOWED_HOSTS` : domaines autorisés à servir l'application.

### Applications (lignes 22-57)
Les apps sont regroupées en trois listes concaténées dans `INSTALLED_APPS` :
- `DJANGO_APPS` : apps natives Django (admin, auth, sessions, staticfiles…).
  `django.contrib.gis` n'est activé que si `USE_GIS=True`.
- `THIRD_PARTY_APPS` : DRF, SimpleJWT (tokens API), django-filter, django-otp
  (2FA TOTP).
- `LOCAL_APPS` : les apps métier du projet (`comptes`, `paroissiens`,
  `sacrements`, `celebrations`, `finances`, `communication`, `api`, `core`,
  `plateforme`).

### Middleware (lignes 59-69)
Chaîne standard Django, avec deux ajouts propres au projet :
- `django_otp.middleware.OTPMiddleware` : gère l'état 2FA de l'utilisateur.
- `apps.comptes.middleware.ParoisseCouranteMiddleware` : détermine la
  **paroisse courante** à partir de l'utilisateur connecté (cœur du
  multi-tenant, §4 du brief).

### Templates (lignes 73-88)
- `DIRS` pointe vers `templates/` à la racine ; `APP_DIRS=True` charge aussi les
  templates de chaque app.
- Context processor maison `apps.comptes.context_processors.navigation_par_role`
  : expose les variables `nav_*` (ex. `nav_finances`) qui affichent ou masquent
  les entrées de menu selon le rôle.

### Base de données (lignes 93-99)
- `DATABASES["default"]` est lue depuis `DATABASE_URL`. **Par défaut SQLite**
  (dev local sans configuration) ; en Docker/production on fournit une URL
  **PostgreSQL** (§16 du brief).

### Authentification (lignes 101-127)
- `AUTH_USER_MODEL = "comptes.Utilisateur"` : modèle utilisateur custom
  (`AbstractUser` + FK paroisse).
- `AUTH_PASSWORD_VALIDATORS` : règles de robustesse des mots de passe.
- `LOGIN_URL` / `LOGIN_REDIRECT_URL` : routes de connexion et de redirection
  après login.

### Internationalisation (lignes 110-113)
- Langue `fr-fr`, fuseau `Africa/Kinshasa` (surchargable via
  `DJANGO_TIME_ZONE`), `USE_TZ=True` (dates stockées en UTC).

### Fichiers statiques et médias (lignes 115-120)
- `STATIC_URL` / `STATIC_ROOT` / `STATICFILES_DIRS` : CSS, JS, images du thème.
- `MEDIA_URL` / `MEDIA_ROOT` : fichiers téléversés (ex. photos de paroissiens).

### API REST — DRF (lignes 129-143)
- Authentification par **JWT** (défaut) et session (pour l'API navigable).
- Accès réservé aux utilisateurs authentifiés, pagination 20 par page,
  filtrage via django-filter.

### JWT — SimpleJWT (lignes 145-150)
- Jeton d'accès valable 30 min, jeton de rafraîchissement 1 jour, rotation
  activée, en-tête `Bearer`.

### Nominatim (lignes 152-156)
- `NOMINATIM_BASE_URL` et `NOMINATIM_USER_AGENT` : géocodage OpenStreetMap
  (consommation d'API externe, §8 du brief). Le `User-Agent` doit rester
  identifiable, conformément à la politique d'usage de Nominatim.

---

## `dev.py` — développement local

Minimaliste : `from .base import *`, puis :
- `DEBUG = True` : pages d'erreur détaillées, rechargement automatique.
- `EMAIL_BACKEND = console` : les e-mails sont **affichés dans le terminal** au
  lieu d'être envoyés (pratique pour tester la 2FA, les notifications…).

La base de données reste celle de `base.py` (SQLite par défaut, ou PostgreSQL
si `DATABASE_URL` est défini, comme sous docker-compose).

---

## `prod.py` — production

`from .base import *`, puis durcissement pour un déploiement Internet
(§4 du brief) :

- `DEBUG = False`.
- **Garde-fou** : lève une erreur au démarrage si `DJANGO_ALLOWED_HOSTS` n'a pas
  été défini (empêche de déployer avec la config de dev).
- **HTTPS / sécurité** : `SECURE_SSL_REDIRECT`, cookies `Secure`, HSTS (30
  jours), `SECURE_PROXY_SSL_HEADER` (derrière un reverse proxy type Render),
  `X_FRAME_OPTIONS = "DENY"`.
- **WhiteNoise** : insère le middleware et le storage compressé/manifesté pour
  servir les fichiers statiques sans serveur web séparé.
- **E-mail SMTP** : backend réel, paramétré par variables d'environnement
  (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`).

---

## Variables d'environnement

Toutes les valeurs sensibles ou dépendantes de l'environnement vivent dans
`.env` (jamais committé). Le modèle est `.env.example` à la racine ; on le
copie et on ajuste :

```bash
cp .env.example .env
```

Principales clés :

| Variable                     | Utilité                                              |
|------------------------------|------------------------------------------------------|
| `DJANGO_SETTINGS_MODULE`     | Fichier de settings à charger (`.dev` ou `.prod`).   |
| `DJANGO_SECRET_KEY`          | Clé de signature (obligatoire en prod).              |
| `DJANGO_DEBUG`               | Active/désactive le mode debug.                      |
| `DJANGO_ALLOWED_HOSTS`       | Domaines autorisés (obligatoire en prod).            |
| `DJANGO_TIME_ZONE`           | Fuseau horaire.                                      |
| `DATABASE_URL`               | Connexion PostgreSQL (sinon SQLite en dev).          |
| `POSTGRES_DB/USER/PASSWORD`  | Identifiants du service `db` de docker-compose.      |
| `NOMINATIM_BASE_URL`         | Endpoint de géocodage.                               |
| `NOMINATIM_USER_AGENT`       | User-Agent identifiable pour Nominatim.              |
| `DJANGO_SECURE_SSL_REDIRECT` | Force HTTPS (prod).                                  |
| `EMAIL_HOST/PORT/USER/…`     | Serveur SMTP (prod).                                 |

> **Règle d'or** : un secret ne doit jamais apparaître dans le code ni dans Git.
> Il passe toujours par une variable d'environnement.
