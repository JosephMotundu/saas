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

## État d'avancement

Le projet est construit par étapes (voir brief).

- ✅ Étape 1 — scaffolding (settings dev/prod, Docker, PostgreSQL, Git)
- ✅ Étape 2 — app `comptes` : modèles `Paroisse`/`Utilisateur`, groupes de
  rôles (Curé, Secrétaire, Trésorier, Lecteur), connexion/déconnexion, admin
- ✅ Fondations des templates — `theme.css` (design tokens + surcharge
  Bootstrap), `base.html`/`base_public.html`/`base_app.html`, app `core`
  (vitrine publique : accueil, fonctionnalités, tarifs, souscription
  simulée ; tableau de bord avec carte Leaflet et compteurs)
- ⏳ Étape 3 — middleware et managers multi-tenant
