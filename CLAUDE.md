# Brief projet — SaaS de gestion paroissiale « ParoisseConnect »

> Ce document est le brief maître à fournir à Claude Code. Colle-le au démarrage
> du projet (ou enregistre-le comme `CLAUDE.md` à la racine du dépôt). Fais
> construire le projet **par étapes**, dans l'ordre de la section « Plan de
> construction », en validant chaque étape avant de passer à la suivante.

---

## 1. Contexte

Application web SaaS de gestion de paroisse catholique, développée comme projet
de fin d'études (L4 Génie Logiciel, UPC/FASI). L'évaluation porte sur des
critères techniques précis (voir §3) : chacun doit être visiblement présent et
défendable. L'application est **multi-tenant** (une instance sert plusieurs
paroisses, données isolées par paroisse) ; pour la soutenance, on simule un seul
client : la **paroisse Saint Raphaël**.

## 2. Stack technique imposée

- **Backend / langage** : Python 3.12, Django 5.x
- **API** : Django REST Framework (DRF)
- **Base de données** : PostgreSQL (SQLite autorisé uniquement en dev local)
- **Frontend** : templates Django + Bootstrap 5 (server-rendered, responsive,
  media queries). Pas de SPA React/Vue. **Bootstrap sert de base grille/responsive
  uniquement — il est surchargé par un thème custom (voir §Direction artistique)
  pour que rien ne ressemble au Bootstrap par défaut.**
- **Carte** : Leaflet (affichage) + géocodage via l'API Nominatim (OpenStreetMap)
- **Auth** : Django auth (mots de passe hachés) + 2FA TOTP + JWT (DRF SimpleJWT)
  pour l'API
- **Conteneurisation** : Docker + docker-compose (services `web` + `db`)
- **Tests** : pytest-django
- **Versioning** : Git (commits atomiques et messages clairs)

## Direction artistique — identité visuelle (NE PAS faire générique)

Le produit ne doit pas ressembler à un template SaaS ni au Bootstrap par défaut.
L'univers de référence est celui d'une paroisse : registres reliés, missels,
pierre, calendrier liturgique. Interface **calme, digne et très lisible** (les
utilisateurs sont un secrétariat paroissial, usage administratif quotidien).

**Signature (l'élément mémorable) : conscience du temps liturgique.** La couleur
d'accent de l'interface suit la saison liturgique en cours (vert / violet /
blanc-or / rouge), et chaque type de sacrement porte sa couleur liturgique de
façon **sémantique** (elle porte du sens, elle ne décore pas).

### Palette — fondée sur le calendrier liturgique
- `--papier` (fond) : `#EFEDE6` (pierre calcaire pâle — PAS un cream chaud générique)
- `--encre` (texte) : `#26201C` (brun-noir, encre de manuscrit, pas noir pur)
- `--brand` (violet liturgique / aubergine) : `#5A2A5C`
- Accents liturgiques fonctionnels :
  - vert (temps ordinaire) : `#3E6B4F`
  - violet (Avent / Carême) : `#5A2A5C`
  - or (fêtes et solennités) : `#B0873C`
  - rouge (Pentecôte / martyrs) : `#9B2D24`
- `--filet` (lignes, règles) : `#D7D1C4`

### Typographie
- **Titres / display** : Cormorant Garamond (ou EB Garamond) — héritage des
  missels imprimés Renaissance, à utiliser avec retenue. Argument défendable.
- **Corps / UI** : Source Sans 3 (ou Inter) — lisible pour les tableaux denses.
- **Données / chiffres** : chiffres tabulaires (registres, finances) pour un
  alignement parfait en colonnes.
- Échelle typographique nette, sentence case partout.

### Mise en page
- Registres sacramentels présentés comme un **registre relié** : lignes réglées,
  numéros d'actes réels (une séquence qui porte une vraie information), chiffres
  tabulaires alignés.
- Navigation latérale sobre, façon onglets de missel ; marges généreuses.
- `border-radius` discret (2–4px), ombres légères, pas d'effets tape-à-l'œil.
- Dépenser l'audace à un seul endroit (la signature liturgique) ; garder tout le
  reste silencieux et discipliné.

### Ton des textes (copy)
- Voix claire, sobre, digne. Verbes actifs : « Enregistrer le baptême », pas
  « Soumettre ». Le libellé d'une action reste le même dans tout le flux.
- Écrans vides = invitation à agir : « Aucun paroissien pour l'instant. Ajoutez
  le premier. » Les erreurs expliquent quoi faire, sans s'excuser.

### Plancher de qualité (non négociable)
Responsive jusqu'au mobile, focus clavier visible, `prefers-reduced-motion`
respecté, contrastes AA.

## 3. Les 16 critères à satisfaire (checklist du jury)

Le code final doit démontrer chacun de ces points :

1. **BDD relationnelle** : modèle entité-association, relations 1:1 et 1:N, clés
   primaires/étrangères, respect des 1re et 2e formes normales, opérations CRUD
   complètes, contraintes d'intégrité (NOT NULL, UNIQUE).
2. **Langage de programmation** backend : Python/Django.
3. **Authentification** : mot de passe haché + **2FA (TOTP)** + **JWT** pour
   l'API.
4. **Déploiement Internet** : projet prêt à déployer (Render ou Railway),
   connexions HTTPS, variables d'environnement pour les secrets.
5. **Responsive design** : Bootstrap 5 + media queries, testé mobile/tablette/desktop.
6. **Architecture MVC** : respecter le pattern MVT de Django (Model / Template =
   Vue / View = Contrôleur), séparation stricte des couches.
7. **Rôles et permissions** : rôles Curé, Secrétaire, Trésorier, Lecteur via les
   Groupes et permissions Django ; accès aux vues protégés selon le rôle.
8. **API RESTful** : (a) **créer** une API REST avec DRF exposant les ressources
   principales ; (b) **consommer** une API externe → géocodage Nominatim pour
   situer la paroisse, rendu sur carte Leaflet.
9. **POO** : modèles et classes de services, méthodes métier sur les modèles,
   couche `services/` pour la logique réutilisable.
10. **Git + dépôt distant** : dépôt GitHub, `.gitignore` correct, historique propre.
11. **Tests unitaires** : pytest-django, couverture des modèles, des règles
    métier (transactions, permissions) et d'au moins un endpoint API.
12. **Docker** : Dockerfile + docker-compose lançant l'app et PostgreSQL.
13. **Automatisation des tâches** : commandes de gestion Django + Makefile pour
    backup BDD, chargement de données de démo (`seed`), lancement des tests.
14. **Transactions et jointures** : `transaction.atomic` sur les opérations
    critiques (ex. `Don` + `RecuFiscal`, `IntentionMesse` + offrande) ;
    optimisation des requêtes avec `select_related`/`prefetch_related`.
15. **Backoffice d'administration** : Django Admin configuré (list_display,
    filtres, recherche) pour toutes les entités, scellé par paroisse.
16. **PostgreSQL** comme SGBD de production.

## 4. Architecture multi-tenant

- Entité `Paroisse` = le **tenant**. Toutes les entités métier portent une clé
  étrangère `paroisse`.
- Un `Utilisateur` (modèle custom `AbstractUser`) appartient à une `Paroisse`.
- Un **middleware** détermine la paroisse courante à partir de l'utilisateur
  connecté et l'expose dans la requête.
- Un **manager/queryset par défaut** filtre automatiquement les données sur la
  paroisse courante, afin d'éviter toute fuite de données entre paroisses.
- Le Django Admin et l'API respectent aussi cette isolation.

## 5. Modèle de données par application Django

Organiser le code en apps Django distinctes :

**`comptes`** (utilisateurs & sécurité)
- `Paroisse` : nom, diocèse, adresse, ville, latitude, longitude (géocodées),
  téléphone, email.
- `Utilisateur(AbstractUser)` : FK `paroisse`, rôle (via Groupe).
- Intégration 2FA TOTP.

**`paroissiens`**
- `Famille` : nom, adresse, téléphone, FK `paroisse`.
- `Paroissien` : nom, prénom, sexe, date de naissance, adresse, téléphone,
  email, photo, FK `famille` (nullable), FK `paroisse`.

**`sacrements`** (registres canoniques)
- `Bapteme` : FK `paroissien`, date, lieu, célébrant, parrain, marraine, numéro
  de registre, FK `paroisse`.
- `Communion`, `Confirmation` : FK `paroissien`, date, célébrant, FK `paroisse`.
- `Mariage` : conjoint 1, conjoint 2, date, célébrant, témoins, FK `paroisse`.
- `Funerailles` : FK `paroissien` (défunt), date, célébrant, FK `paroisse`.
- `MentionMarginale` : FK `bapteme`, type (mariage/ordination/décès…), date,
  référence — permet la mise à jour de l'acte de baptême toute la vie durant.
- Génération de **certificats** imprimables (PDF ou vue imprimable) par acte.

**`celebrations`** (intentions de messe)
- `Celebration` : date, heure, type, célébrant, lieu, FK `paroisse`.
- `IntentionMesse` : demandeur, intention (défunt / action de grâce…), montant
  de l'offrande, statut, FK `celebration`, FK `paroisse`.

**`finances`** (dons)
- `Don` : FK `paroissien` (donateur, nullable pour don anonyme), montant, date,
  type (dîme, offrande, quête…), mode de paiement, FK `paroisse`.
- `RecuFiscal` : FK `don` (1:1), numéro unique, date d'émission.
- Création `Don` + `RecuFiscal` dans une **transaction atomique**.

**`communication`**
- `Annonce` : titre, contenu, date de publication, FK `auteur`, groupe cible,
  FK `paroisse`.

## 6. API REST (DRF)

- Exposer des endpoints pour : paroissiens, célébrations, intentions, dons,
  annonces (lecture + écriture selon permissions).
- Authentification par **JWT** (SimpleJWT).
- Un endpoint qui **consomme Nominatim** pour géocoder l'adresse d'une paroisse
  et renvoyer les coordonnées, affichées ensuite via Leaflet dans une vue web.
- Sérialiseurs, pagination, permissions par rôle.

## 7. Rôles & permissions

- **Curé** : accès complet à sa paroisse.
- **Secrétaire** : gestion paroissiens, sacrements, célébrations, annonces.
- **Trésorier** : gestion des dons et reçus.
- **Lecteur** : consultation seule.
Protéger vues et endpoints en conséquence.

## 8. Qualité, tests, automatisation

- `Makefile` avec cibles : `up`, `down`, `migrate`, `seed`, `test`, `backup`.
- Commande `seed` : crée la paroisse Saint Raphaël, des utilisateurs de chaque
  rôle, et un jeu de données de démonstration réaliste.
- Commande `backup` : export de la base.
- Tests pytest : modèles, isolation multi-tenant, transactions, permissions,
  au moins un endpoint API.

## 9. Plan de construction (ordre impératif)

1. Scaffolding : projet Django, settings (dev/prod), Docker, PostgreSQL, Git.
2. App `comptes` : modèle Paroisse + Utilisateur custom, auth, rôles/groupes.
3. Middleware + managers multi-tenant + tests d'isolation.
4. App `paroissiens` (CRUD + templates responsive + admin).
5. App `sacrements` (registres, mentions marginales, certificats).
6. App `celebrations` (intentions de messe + offrandes, transaction atomique).
7. App `finances` (dons + reçus, transaction atomique).
8. App `communication` (annonces).
9. API DRF + JWT + consommation Nominatim + carte Leaflet.
10. 2FA TOTP.
11. Django Admin complet, Makefile, commandes seed/backup.
12. Tests, README, préparation au déploiement.

**Consignes de travail** : procède app par app, écris les tests au fur et à
mesure, commit à chaque étape avec un message clair, et arrête-toi après chaque
étape pour validation avant de continuer.