# Configuration `config/` — settings, URLs, WSGI/ASGI

Fiche de révision pour la soutenance. Elle documente la **configuration du
projet** Django : le dossier [`config/settings/`](../config/settings/) (réglages
découpés par environnement) ainsi que les fichiers d'entrée
[`config/urls.py`](../config/urls.py), [`config/wsgi.py`](../config/wsgi.py) et
[`config/asgi.py`](../config/asgi.py).

## Rôle de la configuration

`config/` est le **point d'assemblage** du projet : il déclare les applications,
la base de données, la sécurité, l'authentification, l'API, le routage des URLs
et les points d'entrée serveur. La configuration est **découpée par
environnement** (patron *split settings*) : les réglages communs vivent dans
`base.py`, et chaque environnement (`dev.py`, `prod.py`) l'importe puis n'y
ajoute que ses différences. **Aucun secret n'est écrit en dur** : les valeurs
sensibles viennent des **variables d'environnement** (fichier `.env`).

---

## Critères du jury démontrés ici

| Critère (brief §3) | Où le montrer dans le code |
|---|---|
| **§4 — Déploiement Internet (HTTPS, secrets par variables d'environnement)** | [`prod.py`](../config/settings/prod.py) : `SECURE_SSL_REDIRECT`, HSTS, cookies `Secure`, WhiteNoise. [`base.py`](../config/settings/base.py) : `env(...)` lit `.env`. |
| **§16 — PostgreSQL en production** | `DATABASES` lu depuis `DATABASE_URL` (`env.db(...)`), PostgreSQL en Docker/prod, SQLite en dev. |
| **§3 — Authentification (haché + 2FA + JWT)** | `AUTH_USER_MODEL`, `AUTH_PASSWORD_VALIDATORS`, apps `django_otp` (2FA), `REST_FRAMEWORK` + `SIMPLE_JWT`. |
| **§6 — Architecture MVT** | `ROOT_URLCONF`, `TEMPLATES`, `INSTALLED_APPS` structurés en trois groupes. |
| **§8 — API REST + consommation Nominatim** | bloc `REST_FRAMEWORK`, `SIMPLE_JWT`, `NOMINATIM_BASE_URL` / `NOMINATIM_USER_AGENT`. |
| **§4 — Multi-tenant** | `MIDDLEWARE` inclut `apps.comptes.middleware.ParoisseCouranteMiddleware`. |

---

## Comment Django choisit le bon fichier de settings

Django lit la variable d'environnement `DJANGO_SETTINGS_MODULE`. La valeur par
défaut est déjà posée selon le contexte :

| Contexte d'exécution | Valeur utilisée | Défini dans |
|---|---|---|
| `python manage.py …` (local) | `config.settings.dev` | [`manage.py`](../manage.py) |
| Tests (`pytest`) | `config.settings.dev` | [`pytest.ini`](../pytest.ini) |
| `docker-compose up` | `config.settings.dev` | [`docker-compose.yml`](../docker-compose.yml) |
| Serveur WSGI (déploiement) | `config.settings.prod` | [`config/wsgi.py`](../config/wsgi.py) |
| Serveur ASGI (déploiement) | `config.settings.prod` | [`config/asgi.py`](../config/asgi.py) |

On peut toujours forcer un module :
`DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py check`.

---

## `config/settings/base.py` — réglages communs

C'est le fichier importé par tous les autres. Détail par bloc.

### Chargement de l'environnement
```python
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-changeme-in-env")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
```
- `BASE_DIR` : racine du projet (trois niveaux au-dessus du fichier).
- `django-environ` lit `.env` et convertit les types (`env.bool`, `env.list`,
  `env.db`, `env.int`).
- `SECRET_KEY` : clé de signature Django ; **obligatoirement** fournie par
  `DJANGO_SECRET_KEY` en production. La valeur par défaut n'est là que pour le dev.

### Applications — `INSTALLED_APPS`
Les apps sont regroupées en trois listes concaténées :
```python
DJANGO_APPS = [ ...admin, auth, contenttypes, sessions, messages, staticfiles,
                django.contrib.gis si USE_GIS... ]
THIRD_PARTY_APPS = ["rest_framework", "rest_framework_simplejwt",
                    "django_filters", "django_otp",
                    "django_otp.plugins.otp_totp", "django_otp.plugins.otp_static"]
LOCAL_APPS = ["apps.comptes", "apps.core", "apps.paroissiens", "apps.sacrements",
              "apps.celebrations", "apps.finances", "apps.communication",
              "apps.api", "apps.plateforme"]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
```
- `django_otp*` fournit la **2FA TOTP** ; `rest_framework` + `simplejwt` l'API + JWT.
- Ce découpage en trois groupes rend la configuration lisible pour le jury.

### Middleware
```python
MIDDLEWARE = [ ...SecurityMiddleware, SessionMiddleware, CommonMiddleware,
    CsrfViewMiddleware, AuthenticationMiddleware,
    "django_otp.middleware.OTPMiddleware",
    MessageMiddleware,
    "apps.comptes.middleware.ParoisseCouranteMiddleware",
    XFrameOptionsMiddleware ]
```
Deux ajouts propres au projet :
- `OTPMiddleware` : gère l'état de la 2FA de l'utilisateur.
- `ParoisseCouranteMiddleware` : **détermine la paroisse courante** à partir de
  l'utilisateur connecté — cœur du multi-tenant (§4). Placé après
  l'authentification, logique puisqu'il dépend de `request.user`.

### Templates
```python
TEMPLATES = [{ "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
  "OPTIONS": {"context_processors": [ ...debug, request, auth, messages,
      "apps.comptes.context_processors.navigation_par_role" ]}}]
```
- `APP_DIRS=True` charge aussi les templates de chaque app.
- Le context processor maison expose les variables `nav_*` (ex. `nav_finances`)
  qui affichent/masquent les entrées de menu selon le rôle.

### Base de données
```python
DATABASES = {"default": env.db("DATABASE_URL",
             default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
```
- Lue depuis `DATABASE_URL`. **PostgreSQL** en Docker/prod (§16), **SQLite** par
  défaut en dev local (autorisé par le brief uniquement en dev).

### Authentification
```python
AUTH_USER_MODEL = "comptes.Utilisateur"
AUTH_PASSWORD_VALIDATORS = [ ...UserAttributeSimilarity, MinimumLength,
                             CommonPassword, NumericPassword ]
LOGIN_URL = "comptes:connexion"
LOGIN_REDIRECT_URL = "core:tableau_de_bord"
```
- Modèle utilisateur **custom** (`AbstractUser` + FK paroisse) — d'où
  l'importance de définir `AUTH_USER_MODEL` dès le départ.
- Les validateurs imposent la robustesse des mots de passe (hachés par Django).

### Internationalisation
```python
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Africa/Kinshasa")
USE_I18N = True
USE_TZ = True
```
- Langue française, fuseau de Kinshasa, dates stockées en UTC (`USE_TZ`).

### Fichiers statiques et médias
```python
STATIC_URL = "static/"; STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
MEDIA_URL = "media/"; MEDIA_ROOT = BASE_DIR / "media"
```
- `static/` : le thème (CSS/JS). `media/` : fichiers téléversés (photos de
  paroissiens). `STATIC_ROOT` sert au `collectstatic` de production.

### API REST — DRF
```python
REST_FRAMEWORK = {
  "DEFAULT_AUTHENTICATION_CLASSES": (JWTAuthentication, SessionAuthentication),
  "DEFAULT_PERMISSION_CLASSES": (IsAuthenticated,),
  "DEFAULT_PAGINATION_CLASS": PageNumberPagination, "PAGE_SIZE": 20,
  "DEFAULT_FILTER_BACKENDS": (DjangoFilterBackend,) }
```
- Authentification **JWT** par défaut (+ session pour l'API navigable), accès
  réservé aux utilisateurs authentifiés, pagination 20/page, filtrage.

### JWT — SimpleJWT
```python
SIMPLE_JWT = {"ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
  "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
  "ROTATE_REFRESH_TOKENS": True, "AUTH_HEADER_TYPES": ("Bearer",)}
```
- Jeton d'accès 30 min, rafraîchissement 1 jour, rotation activée, en-tête
  `Authorization: Bearer <token>`.

### Nominatim (API externe)
```python
NOMINATIM_BASE_URL = env("NOMINATIM_BASE_URL",
    default="https://nominatim.openstreetmap.org")
NOMINATIM_USER_AGENT = env("NOMINATIM_USER_AGENT", default="paroisseconnect/1.0 ...")
```
- Géocodage OpenStreetMap (§8b, **consommer** une API externe). Le `User-Agent`
  doit rester identifiable, conformément à la politique d'usage de Nominatim.

---

## `config/settings/dev.py` — développement local

Fichier minimaliste :
```python
from .base import *          # noqa
DEBUG = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
```
- `DEBUG = True` : pages d'erreur détaillées, rechargement automatique.
- E-mails **affichés dans le terminal** au lieu d'être envoyés (pratique pour
  tester la 2FA, les notifications…).
- La base reste celle de `base.py` (SQLite par défaut, ou PostgreSQL si
  `DATABASE_URL` est défini, comme sous docker-compose).

---

## `config/settings/prod.py` — production

Importe `base.py` puis **durcit** la configuration pour un déploiement Internet
(§4) :
```python
from .base import *          # noqa
DEBUG = False

# Garde-fou : refuse de démarrer avec la config de dev
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise RuntimeError("DJANGO_ALLOWED_HOSTS doit être défini en production.")

# HTTPS / sécurité
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30      # 30 jours
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
X_FRAME_OPTIONS = "DENY"

# Fichiers statiques servis par WhiteNoise
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STORAGES = {"staticfiles": {"BACKEND":
    "whitenoise.storage.CompressedManifestStaticFilesStorage"}, ...}

# E-mail SMTP réel (paramétré par variables d'environnement)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default=""); EMAIL_PORT = env.int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
```
Points à défendre :
- **Garde-fou `ALLOWED_HOSTS`** : empêche de déployer par erreur avec la config
  de dev (sinon faille de sécurité `Host` header).
- **HTTPS de bout en bout** : redirection SSL, cookies `Secure`, HSTS (le
  navigateur force HTTPS pendant 30 jours), `SECURE_PROXY_SSL_HEADER` pour
  fonctionner derrière un reverse proxy (Render/Railway).
- **WhiteNoise** : sert les fichiers statiques compressés sans serveur web
  séparé — idéal pour un déploiement PaaS simple.

---

## `config/urls.py` — routage racine

`ROOT_URLCONF = "config.urls"`. Ce fichier `include()` les URLs de chaque app
(admin Django, comptes, core, paroissiens, sacrements, celebrations, finances,
communication, api, plateforme, pages publiques). C'est la **table
d'aiguillage** principale : une requête entrante y est associée à la vue de la
bonne app. Les URLs de l'API sont regroupées sous un préfixe (ex. `/api/`).

## `config/wsgi.py` et `config/asgi.py` — points d'entrée serveur

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
application = get_wsgi_application()   # (ou get_asgi_application dans asgi.py)
```
- **WSGI** : interface standard entre le serveur d'application (Gunicorn…) et
  Django, utilisée en production.
- **ASGI** : équivalent asynchrone (websockets, etc.).
- Les deux **posent `config.settings.prod` par défaut** : un serveur de
  production utilise donc automatiquement les réglages durcis.

---

## Variables d'environnement (`.env`)

Toutes les valeurs sensibles ou dépendantes de l'environnement vivent dans
`.env` (jamais committé). Le modèle est [`.env.example`](../.env.example) ; on le
copie : `cp .env.example .env`.

| Variable | Utilité |
|---|---|
| `DJANGO_SETTINGS_MODULE` | Fichier de settings à charger (`.dev` ou `.prod`). |
| `DJANGO_SECRET_KEY` | Clé de signature (obligatoire en prod). |
| `DJANGO_DEBUG` | Active/désactive le mode debug. |
| `DJANGO_ALLOWED_HOSTS` | Domaines autorisés (obligatoire en prod). |
| `DJANGO_TIME_ZONE` | Fuseau horaire. |
| `DATABASE_URL` | Connexion PostgreSQL (sinon SQLite en dev). |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Identifiants du service `db` de docker-compose. |
| `NOMINATIM_BASE_URL` / `NOMINATIM_USER_AGENT` | Géocodage Nominatim. |
| `DJANGO_SECURE_SSL_REDIRECT` | Force HTTPS (prod). |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Serveur SMTP (prod). |

> **Règle d'or** : un secret n'apparaît jamais dans le code ni dans Git ; il
> passe toujours par une variable d'environnement.

---

## Questions probables du jury & réponses

1. **Pourquoi avoir découpé les settings en `base` / `dev` / `prod` ?**
   Pour éviter un unique fichier truffé de `if DEBUG`. Les réglages communs sont
   dans `base.py` ; chaque environnement n'exprime que ses différences. C'est
   lisible, moins risqué (on ne déploie pas la config de dev par erreur) et
   c'est une pratique standard.

2. **Comment gérez-vous les secrets (clé secrète, mot de passe BDD) ?**
   Via des variables d'environnement lues avec `django-environ` depuis un
   fichier `.env` non versionné. Le dépôt ne contient que `.env.example` (des
   valeurs factices). En production, les variables sont fournies par la
   plateforme d'hébergement.

3. **SQLite ou PostgreSQL ?**
   PostgreSQL en production et sous Docker (via `DATABASE_URL`), SQLite
   uniquement en dev local pour démarrer sans installer de base. Le code ne
   change pas : seule l'URL de connexion change.

4. **Comment le projet force-t-il HTTPS ?**
   Dans `prod.py` : `SECURE_SSL_REDIRECT` (redirige HTTP→HTTPS), cookies
   `Secure`, en-tête HSTS (le navigateur mémorise qu'il faut du HTTPS), et
   `SECURE_PROXY_SSL_HEADER` pour reconnaître le HTTPS derrière un proxy.

5. **À quoi sert le garde-fou sur `ALLOWED_HOSTS` ?**
   À refuser de démarrer en production si `DJANGO_ALLOWED_HOSTS` n'a pas été
   défini : cela empêche un déploiement accidentel avec les hôtes de dev, ce qui
   serait une faille (`Host` header).

6. **Où est activée la 2FA et le JWT dans la configuration ?**
   La 2FA : apps `django_otp` + `OTPMiddleware`. Le JWT : `rest_framework_simplejwt`
   dans `INSTALLED_APPS`, `JWTAuthentication` dans `REST_FRAMEWORK`, et les
   durées de vie des jetons dans `SIMPLE_JWT`.

7. **Différence entre WSGI et ASGI ?**
   Deux interfaces entre le serveur et Django : WSGI (synchrone, utilisé ici en
   production) et ASGI (asynchrone, pour websockets). Les deux chargent
   `config.settings.prod` par défaut.

8. **Comment les statiques sont-ils servis en production ?**
   Par WhiteNoise (`CompressedManifestStaticFilesStorage`), après un
   `collectstatic` vers `STATIC_ROOT`. Pas besoin d'un serveur web séparé pour
   les fichiers statiques.

9. **Où est déclaré le modèle utilisateur custom ?**
   `AUTH_USER_MODEL = "comptes.Utilisateur"` dans `base.py`, défini avant la
   première migration — c'est ce qui permet d'ajouter la FK `paroisse` sur
   l'utilisateur.
