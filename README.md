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

```bash
python3 -m venv .venv && source .venv/bin/activate
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

Le projet est construit par étapes (voir brief). Étape courante : scaffolding
initial (settings dev/prod, Docker, PostgreSQL, Git).
