# Documentation de révision — ParoisseConnect

Ce dossier rassemble une **fiche par application Django**, pensée pour réviser
et **défendre le projet devant le jury**. Chaque fiche explique, fichier par
fichier, le code de l'app, relie chaque partie aux **16 critères du jury**
(voir [`../CLAUDE.md`](../CLAUDE.md)), et se termine par des **questions
probables du jury avec leurs réponses**.

## Les fiches par application

| Fiche | Rôle de l'application |
|-------|-----------------------|
| [comptes.md](comptes.md) | Utilisateurs, authentification (mot de passe haché, 2FA TOTP, JWT), rôles/groupes, et **cœur du multi-tenant** (modèle `Paroisse` = tenant, manager par défaut, middleware, ContextVar). |
| [paroissiens.md](paroissiens.md) | Registre des familles et des paroissiens (CRUD complet, photo, relation 1:N Famille→Paroissien). |
| [sacrements.md](sacrements.md) | Registres canoniques (baptême, communion, confirmation, mariage, funérailles), mentions marginales, certificats imprimables. |
| [celebrations.md](celebrations.md) | Célébrations (messes) et intentions de messe avec offrande (montant + devise). |
| [finances.md](finances.md) | Dons, dépenses, offrandes de messe, reçus fiscaux ; **solde par devise** ; **transaction atomique** ; couche services. |
| [communication.md](communication.md) | Annonces paroissiales + page publique par paroisse (URLs internes vs publiques). |
| [api.md](api.md) | API REST (DRF) : sérialiseurs, ViewSets, **JWT**, permissions par rôle, isolation multi-tenant, et **consommation de l'API Nominatim** (géocodage → carte Leaflet). |
| [core.md](core.md) | Tableau de bord, pages publiques, **inscription d'une paroisse**, `ContenuVitrine`, et le **module partagé de devises** (`devises.py`). |
| [plateforme.md](plateforme.md) | Espace **superadmin** : supervision de toutes les paroisses (activer/suspendre/supprimer), reset de mot de passe, édition de la vitrine. |
| [settings.md](settings.md) | **Configuration `config/`** : settings découpés dev/prod, `INSTALLED_APPS`, middleware, base de données, DRF/JWT, sécurité HTTPS, URLs, WSGI/ASGI, variables d'environnement. |

## Carte des 16 critères du jury → où les défendre

| # | Critère | Fiche(s) principale(s) |
|---|---------|------------------------|
| 1 | BDD relationnelle (1:1, 1:N, PK/FK, contraintes) | [paroissiens](paroissiens.md), [sacrements](sacrements.md), [finances](finances.md) |
| 2 | Langage backend (Python/Django) | toutes |
| 3 | Authentification (haché + 2FA TOTP + JWT) | [comptes](comptes.md), [api](api.md) |
| 4 | Déploiement Internet (HTTPS, secrets) | [settings](settings.md) |
| 5 | Responsive design | [core](core.md), [paroissiens](paroissiens.md) (templates) |
| 6 | Architecture MVC/MVT | toutes (section « une section par fichier ») |
| 7 | Rôles et permissions (Groupes) | [comptes](comptes.md), + chaque app métier |
| 8 | API REST : créer + consommer (Nominatim) | [api](api.md) |
| 9 | POO (services, méthodes métier) | [finances](finances.md), [comptes](comptes.md), [plateforme](plateforme.md) |
| 10 | Git + dépôt distant | historique Git du dépôt |
| 11 | Tests unitaires (pytest-django) | section « Tests » de chaque fiche |
| 12 | Docker (Dockerfile + compose) | racine du dépôt (`Dockerfile`, `docker-compose.yml`) |
| 13 | Automatisation (commandes + Makefile) | [comptes](comptes.md) (commande `seed`), `Makefile` |
| 14 | Transactions et jointures | [finances](finances.md) (transaction atomique, `select_related`, agrégations) |
| 15 | Backoffice d'administration | section « admin.py » de chaque fiche |
| 16 | PostgreSQL en production | [settings](settings.md) |

## Concepts transverses à maîtriser

- **Multi-tenant (isolation par paroisse)** — expliqué en profondeur dans
  [comptes.md](comptes.md) : le modèle `Paroisse` (tenant), le manager par défaut
  qui filtre automatiquement, le middleware qui pose la paroisse courante, et la
  défense en profondeur via `FiltrageParoisseMixin`.
- **Devise unique par montant, solde par devise** — [finances.md](finances.md) et
  [core.md](core.md) (`devises.py`) : dollars et francs ne s'additionnent jamais.
- **Superadmin vs Curé** — [plateforme.md](plateforme.md) : qui échappe au
  filtrage multi-tenant et pourquoi.
