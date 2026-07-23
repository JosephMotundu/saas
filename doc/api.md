# L'app `api` — API REST (DRF + JWT) de ParoisseConnect

> Fiche de révision pour la soutenance. Objectif : pouvoir **défendre** ligne par
> ligne l'API REST du projet. Tout ce qui suit est tiré du code réel de
> [`apps/api/`](../apps/api) ; aucun exemple n'est inventé.

## Rôle de l'app `api`

L'app `api` regroupe **toute la surface REST** du SaaS. Elle ne définit aucun
modèle : elle **expose** les modèles des autres apps (`paroissiens`,
`celebrations`, `finances`, `communication`) via Django REST Framework (DRF), et
elle **consomme** une API externe (Nominatim / OpenStreetMap) pour le géocodage.

Elle démontre donc, à elle seule, deux critères du jury bien distincts :
- **créer** une API REST (§8a) ;
- **consommer** une API REST externe (§8b).

L'app est déclarée dans [`apps.py`](../apps/api/apps.py) avec `label = "api"` et
`verbose_name = "API"`, et montée sous le préfixe `/api/` dans
[`config/urls.py`](../config/urls.py) :

```python
path("api/", include("apps.api.urls")),
```

Toutes les routes ci-dessous sont donc préfixées par `/api/`.

---

## Critères du jury démontrés ici

| Critère | Où le montrer dans l'app `api` |
|--------|-------------------------------|
| **§8a — Créer une API REST** | 5 `ModelViewSet` (paroissiens, célébrations, intentions, dons, annonces) enregistrés sur un `DefaultRouter` dans [`urls.py`](../apps/api/urls.py) ; sérialiseurs dans [`serializers.py`](../apps/api/serializers.py) |
| **§8b — Consommer une API externe (Nominatim)** | `GeocoderParoisseView`, `GeocoderInverseView`, `RechercherAdresseView` dans [`views.py`](../apps/api/views.py) : appels HTTP `requests.get` vers Nominatim, résultat affiché sur carte Leaflet |
| **§3 — Authentification JWT** | `ObtenirJetonView` + `TokenRefreshView`, réglages `SIMPLE_JWT` dans [`config/settings/base.py`](../config/settings/base.py) ; jeton refusé si paroisse suspendue (`ParoisseSuspendueTokenObtainPairSerializer`) |
| **§7 — Rôles et permissions** | Fabrique `creer_permission_role` dans [`permissions.py`](../apps/api/permissions.py), appliquée à chaque ViewSet |
| **§4 — Isolation multi-tenant** | `IsolationParoisseMixin` dans [`mixins.py`](../apps/api/mixins.py) : filtre chaque queryset sur `request.user.paroisse` |
| **§11 — Tests d'endpoint** | 5 fichiers dans [`apps/api/tests/`](../apps/api/tests) couvrant JWT, dons+reçu, permissions, isolation, géocodage |
| **§14 — Transaction atomique via l'API** | `DonViewSet.perform_create` délègue à `enregistrer_don_avec_recu` (`@transaction.atomic`) |

---

## Réglages globaux (settings)

Tout part de deux blocs de [`config/settings/base.py`](../config/settings/base.py).

### `REST_FRAMEWORK`

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}
```

Ce que le jury doit vous entendre expliquer :
- **Deux modes d'authentification** acceptés : le JWT (pour un client API pur,
  ex. `curl`, mobile) **et** la session Django (pratique pour tester dans un
  navigateur connecté). Par défaut, tout endpoint exige un utilisateur
  authentifié (`IsAuthenticated`).
- **Pagination** : `PageNumberPagination`, **20 objets par page**. C'est pour ça
  que les réponses de liste ont la forme `{"count", "next", "previous",
  "results": [...]}` — un point que les tests vérifient (`reponse.data["count"]`,
  `reponse.data["results"]`).
- **Filtrage** : `DjangoFilterBackend` est branché globalement, ce qui autorise
  le filtrage par paramètres d'URL sur les ViewSets (mécanisme prêt à l'emploi).

### `SIMPLE_JWT`

```python
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
```

- Le **jeton d'accès** (access) vit **30 minutes** ; le **jeton de
  rafraîchissement** (refresh) vit **1 jour**.
- `ROTATE_REFRESH_TOKENS = True` : à chaque rafraîchissement, un nouveau refresh
  est émis (limite le vol de jeton dans la durée).
- `AUTH_HEADER_TYPES = ("Bearer",)` : les requêtes s'authentifient avec l'en-tête
  `Authorization: Bearer <access>`.

### Nominatim

```python
NOMINATIM_BASE_URL = env("NOMINATIM_BASE_URL", default="https://nominatim.openstreetmap.org")
NOMINATIM_USER_AGENT = env("NOMINATIM_USER_AGENT", default="paroisseconnect/1.0 (...)")
```

L'URL de base **et** le `User-Agent` sont des **variables d'environnement** (avec
valeur par défaut). Le `User-Agent` est **exigé par la politique d'usage de
Nominatim** — un test le vérifie explicitement.

---

## Fichier par fichier

### [`apps/api/serializers.py`](../apps/api/serializers.py) — traduction modèle ⇄ JSON

Un **sérialiseur** convertit un objet Python/Django en JSON (sortie) et valide le
JSON entrant avant de créer/modifier un objet (entrée). C'est la couche « V » de
l'API.

**`ParoisseSuspendueTokenObtainPairSerializer`** — surcharge le sérialiseur JWT
standard pour **bloquer l'émission d'un jeton si la paroisse est suspendue** :

```python
class ParoisseSuspendueTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        donnees = super().validate(attrs)  # vérifie username/mot de passe
        paroisse = self.user.paroisse
        if paroisse is not None and not paroisse.est_active:
            raise AuthenticationFailed("Votre paroisse a été suspendue. ...",
                                       code="paroisse_suspendue")
        return donnees
```

Argument défendable : c'est **le même contrôle** que le formulaire de connexion
web (`apps.comptes.forms`). Le compte peut être valide, mais si la plateforme a
suspendu la paroisse (impayé, décision admin), aucun jeton n'est délivré.

**`ParoissienSerializer`** — expose les champs métier d'un paroissien
(`nom, prenom, sexe, date_naissance, adresse, telephone, email, photo, famille`).
Point clé, le `__init__` **restreint la clé étrangère `famille`** aux familles de
la paroisse de l'utilisateur :

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    request = self.context.get("request")
    if request is not None and request.user.is_authenticated:
        self.fields["famille"].queryset = Famille.objects.filter(
            paroisse=request.user.paroisse
        )
```

Sans ça, un utilisateur pourrait rattacher un paroissien à une `Famille` d'une
**autre** paroisse (fuite inter-tenant par la porte de derrière). Le même motif
protège `IntentionMesseSerializer` (champ `celebration`) et `DonSerializer`
(champ `paroissien`).

**`CelebrationSerializer`** — ajoute un champ **lecture seule**
`type_celebration_affiche` qui renvoie le libellé lisible (`get_..._display`) en
plus du code brut. Pratique pour l'affichage sans requête supplémentaire.

**`IntentionMesseSerializer`** — expose `demandeur, intention, montant_offrande,
devise, statut`, avec `statut_affiche` (libellé lisible) et restriction du champ
`celebration` à la paroisse courante.

**`RecuFiscalSerializer`** — mini-sérialiseur (`numero, date_emission`), **imbriqué
en lecture seule** dans le don.

**`DonSerializer`** :

```python
class DonSerializer(serializers.ModelSerializer):
    recu_fiscal = RecuFiscalSerializer(read_only=True)
    class Meta:
        model = Don
        fields = ["id", "paroissien", "montant", "devise", "date",
                  "type_don", "mode_paiement", "recu_fiscal"]
    def __init__(self, *args, **kwargs):
        ...
        self.fields["paroissien"].required = False
        self.fields["paroissien"].allow_null = True
```

À défendre : `recu_fiscal` est **en lecture seule** — on ne l'envoie jamais, il
est **généré côté serveur** dans la même transaction que le don (voir la vue). Le
champ `paroissien` est **optionnel/nullable** parce que le brief prévoit le **don
anonyme**.

**`AnnonceSerializer`** — `auteur` est un `StringRelatedField` en lecture seule
(on affiche le nom, on ne le fixe pas depuis le client : la vue met l'auteur =
utilisateur connecté).

---

### [`apps/api/permissions.py`](../apps/api/permissions.py) — rôles par rôle liturgique

Une seule fonction, `creer_permission_role(roles_lecture, roles_ecriture)`, qui
**fabrique** une classe de permission DRF paramétrée. C'est une *factory* : on la
règle par ViewSet.

```python
def creer_permission_role(roles_lecture=(), roles_ecriture=()):
    class PermissionRole(BasePermission):
        def has_permission(self, request, view):
            utilisateur = request.user
            if not utilisateur or not utilisateur.is_authenticated:
                return False
            if utilisateur.paroisse is not None and not utilisateur.paroisse.est_active:
                return False                       # paroisse suspendue -> refus
            if utilisateur.is_superuser:
                return True
            groupes = set(utilisateur.groups.values_list("name", flat=True))
            if "Curé" in groupes:
                return True                        # Curé = accès complet
            roles_autorises = roles_lecture if request.method in SAFE_METHODS else roles_ecriture
            return bool(groupes & set(roles_autorises))
    return PermissionRole
```

Logique à réciter au jury :
1. Non authentifié → refus.
2. Paroisse suspendue → refus (double du contrôle JWT, mais couvre aussi les
   jetons **déjà émis** avant la suspension).
3. Superuser → autorisé.
4. **Curé** → toujours autorisé (accès complet à sa paroisse, §7).
5. Sinon, on distingue **lecture** (méthodes `SAFE_METHODS` = GET/HEAD/OPTIONS)
   et **écriture** (POST/PUT/PATCH/DELETE) : le rôle doit figurer dans la liste
   correspondante.

C'est l'**équivalent API** du `RoleRequisMixin` utilisé côté web
(`apps.comptes.mixins`) — même politique, deux points d'entrée.

Les listes de rôles sont définies en haut de [`views.py`](../apps/api/views.py) :

```python
ROLES_PASTORALE_LECTURE = ("Secrétaire", "Lecteur")
ROLES_PASTORALE_ECRITURE = ("Secrétaire",)
ROLES_FINANCES_LECTURE = ("Trésorier", "Lecteur")
ROLES_FINANCES_ECRITURE = ("Trésorier",)
```

Traduction : le **Lecteur** lit partout mais n'écrit nulle part ; le
**Secrétaire** gère la pastorale (paroissiens, célébrations, intentions,
annonces) ; le **Trésorier** gère les finances (dons) ; le **Curé** peut tout.

---

### [`apps/api/mixins.py`](../apps/api/mixins.py) — isolation multi-tenant de l'API

`IsolationParoisseMixin` est le cœur de la sécurité multi-tenant côté API.

```python
class IsolationParoisseMixin:
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.paroisse is None:
            return queryset.none()
        return queryset.filter(paroisse=self.request.user.paroisse)

    def exiger_paroisse(self):
        if self.request.user.paroisse is None:
            raise PermissionDenied("Un superadministrateur ne peut pas créer ...")
        return self.request.user.paroisse

    def perform_create(self, serializer):
        serializer.save(paroisse=self.exiger_paroisse())
```

**Le point subtil à connaître absolument** (c'est écrit dans la docstring) : le
projet a un manager par défaut qui filtre automatiquement par paroisse, mais il
s'appuie sur une `ContextVar` positionnée par un **middleware Django**. Or ce
middleware s'exécute **avant** que DRF authentifie la requête par JWT
(l'authentification JWT n'a lieu que dans `APIView.dispatch()`). Pour une requête
authentifiée **uniquement par jeton** (sans cookie de session), la `ContextVar`
ne serait donc pas fiable.

**Conclusion à défendre** : le mixin **ne fait pas confiance** au manager
automatique et **refiltre explicitement** sur `request.user.paroisse`. C'est une
ceinture-et-bretelles délibérée, pas une redondance accidentelle.

Trois conséquences :
- `get_queryset` : on ne voit **que** sa paroisse ; un superadmin sans paroisse
  voit `queryset.none()`.
- Le **détail** d'un objet d'une autre paroisse renvoie **404** (l'objet n'est pas
  dans le queryset filtré) — testé.
- `perform_create` **impose** la paroisse de l'utilisateur : on ne peut pas créer
  un objet « pour » une autre paroisse, même en trichant sur le corps de la
  requête.

---

### [`apps/api/views.py`](../apps/api/views.py) — les vues (contrôleurs)

**`ObtenirJetonView`** — remplace la vue JWT standard pour brancher le
sérialiseur qui bloque les paroisses suspendues :

```python
class ObtenirJetonView(TokenObtainPairView):
    serializer_class = ParoisseSuspendueTokenObtainPairSerializer
```

**Les 5 ViewSets** suivent tous le même patron : `IsolationParoisseMixin` +
`viewsets.ModelViewSet` (= CRUD complet : list, retrieve, create, update,
partial_update, destroy), un `queryset` optimisé, et une paire de permissions
`[IsAuthenticated, creer_permission_role(...)]`.

| ViewSet | Modèle | Queryset optimisé | Rôles |
|--------|--------|-------------------|-------|
| `ParoissienViewSet` | `Paroissien` | `select_related("famille")` | pastorale |
| `CelebrationViewSet` | `Celebration` | tri `date, heure` | pastorale |
| `IntentionMesseViewSet` | `IntentionMesse` | `select_related("celebration")` | pastorale |
| `DonViewSet` | `Don` | `select_related("paroissien", "recu_fiscal")` | finances |
| `AnnonceViewSet` | `Annonce` | `select_related("auteur", "groupe_cible")` | pastorale |

Les `select_related` sont là pour le critère **§14 (optimisation des requêtes,
jointures SQL)** : on charge les relations en une seule requête au lieu de N+1.

Les ViewSets qui ont un sérialiseur à filtrage de FK (paroissiens, intentions,
dons) surchargent `get_serializer_context` pour **passer la requête** au
sérialiseur (c'est ce `request` qui alimente le filtrage de la FK par paroisse).

**`DonViewSet` — le cas de la transaction atomique (§14)** :

```python
def perform_create(self, serializer):
    donnees = serializer.validated_data
    don, _recu = enregistrer_don_avec_recu(
        paroisse=self.exiger_paroisse(),
        montant=donnees["montant"],
        devise=donnees.get("devise", "CDF"),
        date=donnees["date"],
        type_don=donnees["type_don"],
        mode_paiement=donnees["mode_paiement"],
        paroissien=donnees.get("paroissien"),
    )
    serializer.instance = don
```

Au lieu du `perform_create` générique (qui ferait un simple `save`), le don passe
par le **service métier** `enregistrer_don_avec_recu` de
[`apps/finances/services.py`](../apps/finances/services.py), décoré
`@transaction.atomic`. Ce service crée le `Don` **et** son `RecuFiscal` dans une
seule transaction : soit les deux existent, soit aucun. Ainsi, **un don créé via
l'API obtient son reçu fiscal exactement comme depuis l'interface web** — la
logique métier n'est pas dupliquée, elle est réutilisée (critère §9, POO / couche
services).

**`AnnonceViewSet.perform_create`** — fixe l'auteur et la paroisse côté serveur :

```python
def perform_create(self, serializer):
    serializer.save(paroisse=self.exiger_paroisse(), auteur=self.request.user)
```

#### Les trois vues de géocodage (consommation de Nominatim, §8b)

Ce sont des `APIView` (pas des ViewSets) car elles ne font pas de CRUD sur un
modèle : elles **appellent une API tierce**.

**`GeocoderParoisseView` (POST, réservé au Curé)** — géocodage **direct**
(adresse → coordonnées), puis **enregistrement** sur la paroisse :

```python
class GeocoderParoisseView(APIView):
    permission_classes = [IsAuthenticated, creer_permission_role()]  # roles vides -> Curé/superuser seuls

    def post(self, request):
        paroisse = request.user.paroisse
        ...
        adresse = ", ".join(p for p in [paroisse.adresse, paroisse.ville, paroisse.diocese] if p)
        reponse = requests.get(
            f"{settings.NOMINATIM_BASE_URL}/search",
            params={"q": adresse, "format": "json", "limit": 1},
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            timeout=5,
        )
        reponse.raise_for_status()
        resultats = reponse.json()
        ...
        paroisse.latitude = round(float(resultats[0]["lat"]), 6)
        paroisse.longitude = round(float(resultats[0]["lon"]), 6)
        paroisse.save(update_fields=["latitude", "longitude"])
        return Response({"latitude": paroisse.latitude, "longitude": paroisse.longitude})
```

Points à défendre :
- **`creer_permission_role()`** sans argument → aucun rôle en lecture ni en
  écriture → seuls le **Curé** et le superuser passent. Modifier la localisation
  officielle de la paroisse n'est pas une action de consultation courante.
- **`User-Agent` obligatoire** (politique Nominatim) et **`timeout=5`** (on ne
  bloque pas le serveur si Nominatim rame).
- Gestion d'erreurs : `requests.RequestException` → **503** (service
  indisponible) ; aucun résultat → **404** (adresse introuvable).
- **`round(..., 6)`** : Nominatim renvoie parfois >6 décimales ; les champs
  `latitude/longitude` de `Paroisse` sont `decimal_places=6, max_digits=9`. Sans
  l'arrondi, PostgreSQL lève `numeric field overflow` en production. Détail
  couvert par un test dédié.

Les coordonnées enregistrées sont ensuite **affichées sur la carte Leaflet** du
tableau de bord : c'est la boucle complète du critère §8b (consommer une API
externe **et** restituer le résultat cartographiquement).

**`GeocoderInverseView` (GET, public)** — géocodage **inverse** (coordonnées →
adresse). Utilisé sur la **page de souscription** (avant toute création de
compte, d'où `AllowAny`) : cliquer sur la carte remplit automatiquement les
champs avenue/quartier/commune/ville. La vue interroge `/reverse` de Nominatim,
puis **normalise** la réponse OSM (souvent hétérogène) en essayant plusieurs clés
(`city` / `town` / `village`…). Erreurs : `lat`/`lon` manquants → 400 ; `error`
dans la réponse → 404.

**`RechercherAdresseView` (GET, public)** — recherche **texte → coordonnées** :
combine les champs déjà saisis en une requête `q`, appelle `/search` (`limit=5`)
et renvoie une liste de candidats `{latitude, longitude, affichage}`. Si aucun
champ n'est fourni → 400.

---

### [`apps/api/urls.py`](../apps/api/urls.py) — le routage

```python
router = DefaultRouter()
router.register("paroissiens", ParoissienViewSet, basename="paroissien")
router.register("celebrations", CelebrationViewSet, basename="celebration")
router.register("intentions", IntentionMesseViewSet, basename="intention")
router.register("dons", DonViewSet, basename="don")
router.register("annonces", AnnonceViewSet, basename="annonce")

urlpatterns = [
    path("jeton/", ObtenirJetonView.as_view(), name="jeton_obtenir"),
    path("jeton/rafraichir/", TokenRefreshView.as_view(), name="jeton_rafraichir"),
    path("paroisse/geocoder/", GeocoderParoisseView.as_view(), name="paroisse_geocoder"),
    path("geocoder-inverse/", GeocoderInverseView.as_view(), name="geocoder_inverse"),
    path("rechercher-adresse/", RechercherAdresseView.as_view(), name="rechercher_adresse"),
    path("", include(router.urls)),
]
```

Le **`DefaultRouter`** génère automatiquement les routes REST de chaque ViewSet
(list + create sur la collection, retrieve + update + delete sur l'élément).
`app_name = "api"` permet le `reverse("api:...")` utilisé partout dans les tests.

**Table des routes** (préfixe `/api/` inclus) :

| Méthode + URL | Vue | Rôle requis |
|---------------|-----|-------------|
| `POST /api/jeton/` | `ObtenirJetonView` | public (identifiants valides) |
| `POST /api/jeton/rafraichir/` | `TokenRefreshView` | refresh valide |
| `GET/POST /api/paroissiens/` | `ParoissienViewSet` | lecture: Sec./Lect./Curé — écriture: Sec./Curé |
| `GET/PUT/PATCH/DELETE /api/paroissiens/{id}/` | idem | idem |
| `GET/POST /api/celebrations/` | `CelebrationViewSet` | idem pastorale |
| `GET/POST /api/intentions/` | `IntentionMesseViewSet` | idem pastorale |
| `GET/POST /api/dons/` | `DonViewSet` | lecture: Trés./Lect./Curé — écriture: Trés./Curé |
| `GET/POST /api/annonces/` | `AnnonceViewSet` | idem pastorale |
| `POST /api/paroisse/geocoder/` | `GeocoderParoisseView` | Curé / superuser |
| `GET /api/geocoder-inverse/` | `GeocoderInverseView` | public |
| `GET /api/rechercher-adresse/` | `RechercherAdresseView` | public |

---

## Comment tester l'API (exemples concrets)

Tous les exemples utilisent l'utilisateur de démonstration `secretaire1` (rôle
Secrétaire) créé par la commande `seed`. Adaptez l'hôte à votre environnement.

### 1. Obtenir un couple de jetons

```bash
curl -X POST http://localhost:8000/api/jeton/ \
     -H "Content-Type: application/json" \
     -d '{"username": "secretaire1", "password": "mot-de-passe-test-123"}'
```

Réponse :

```json
{ "access": "eyJhbGciOi...", "refresh": "eyJhbGciOi..." }
```

### 2. Appeler un endpoint protégé avec le jeton Bearer

```bash
curl http://localhost:8000/api/paroissiens/ \
     -H "Authorization: Bearer eyJhbGciOi...<access>..."
```

Réponse (paginée, 20/page) :

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    { "id": 1, "nom": "Mbala", "prenom": "Jean", "sexe": "M", "famille": null, ... }
  ]
}
```

Sans l'en-tête `Authorization`, la même requête renvoie **401**.

### 3. Créer un paroissien (écriture — rôle Secrétaire)

```bash
curl -X POST http://localhost:8000/api/paroissiens/ \
     -H "Authorization: Bearer <access>" \
     -H "Content-Type: application/json" \
     -d '{"nom": "Kalonji", "prenom": "Marie", "sexe": "F"}'
```

→ **201 Created**. La paroisse n'est **pas** dans le corps : elle est imposée par
le serveur (`perform_create`).

### 4. Créer un don (le reçu fiscal est généré automatiquement — rôle Trésorier)

```bash
curl -X POST http://localhost:8000/api/dons/ \
     -H "Authorization: Bearer <access-tresorier>" \
     -H "Content-Type: application/json" \
     -d '{"montant": "25.00", "date": "2026-03-01", "type_don": "offrande", "mode_paiement": "especes"}'
```

Réponse **201** — noter le `recu_fiscal` imbriqué, créé dans la même transaction :

```json
{ "id": 1, "montant": "25.00", ..., "recu_fiscal": { "numero": "REC-2026-0001", "date_emission": "2026-03-01" } }
```

### 5. Rafraîchir un jeton d'accès expiré

```bash
curl -X POST http://localhost:8000/api/jeton/rafraichir/ \
     -H "Content-Type: application/json" \
     -d '{"refresh": "<refresh>"}'
```

### 6. Géocoder la paroisse (Curé uniquement)

```bash
curl -X POST http://localhost:8000/api/paroisse/geocoder/ \
     -H "Authorization: Bearer <access-cure>"
```

→ `{ "latitude": "-4.305737", "longitude": "15.302001" }`, coordonnées ensuite
tracées par Leaflet sur le tableau de bord.

---

## Les tests ([`apps/api/tests/`](../apps/api/tests))

Tous les fichiers utilisent `pytest.mark.django_db` et l'`APIClient` de DRF.

### [`test_jwt.py`](../apps/api/tests/test_jwt.py) — authentification JWT
- `test_obtenir_un_jeton_avec_des_identifiants_valides` : POST `/jeton/` valide →
  200 avec `access` + `refresh`.
- `test_jeton_refuse_avec_un_mauvais_mot_de_passe` : mauvais mot de passe → 401.
- `test_le_jeton_permet_d_acceder_a_un_endpoint_protege` : sans jeton → 401 ;
  avec `Bearer <access>` → 200.
- `test_jeton_refuse_si_la_paroisse_est_suspendue` : paroisse `est_active=False`
  → l'émission du jeton est refusée (401).
- `test_jeton_deja_emis_refuse_apres_suspension` : un jeton **valide** émis
  **avant** suspension → une fois la paroisse suspendue, l'accès renvoie **403**
  (c'est la couche `permissions.py` qui rattrape, pas le sérialiseur JWT).

### [`test_dons_api.py`](../apps/api/tests/test_dons_api.py) — transaction + rôle
- `test_creer_un_don_via_l_api_genere_aussi_le_recu_fiscal` : POST `/dons/` (rôle
  Trésorier) → 201, `recu_fiscal.numero == "REC-2026-0001"`, et le `RecuFiscal`
  existe bien en base. **La preuve de la transaction atomique via l'API.**
- `test_secretaire_n_a_pas_acces_aux_dons` : un Secrétaire sur `/dons/` → **403**
  (cloison pastorale ⇄ finances).

### [`test_paroissiens_api.py`](../apps/api/tests/test_paroissiens_api.py) — CRUD + rôles
- `test_secretaire_peut_lister_et_creer_des_paroissiens` : liste 200 + création
  201 ; le paroissien créé porte bien la paroisse de l'utilisateur.
- `test_lecteur_peut_lire_mais_pas_ecrire` : Lecteur → GET 200, POST **403**
  (méthodes sûres vs non sûres).
- `test_tresorier_n_a_pas_acces_aux_paroissiens` : Trésorier sur `/paroissiens/`
  → **403**.

### [`test_isolation_api.py`](../apps/api/tests/test_isolation_api.py) — multi-tenant
- `test_la_liste_api_ne_montre_que_la_paroisse_courante` : deux paroisses, deux
  paroissiens ; le Secrétaire de Saint Raphaël ne voit **que** « Mbala ».
- `test_le_detail_d_un_autre_tenant_est_introuvable` : GET du détail d'un
  paroissien d'une autre paroisse → **404** (pas 403 : l'objet n'existe pas *pour
  lui*).
- `test_superadmin_sans_paroisse_ne_peut_pas_creer_de_paroissien` : superadmin
  sans paroisse → POST **403** (via `exiger_paroisse`).

### [`test_geocodage.py`](../apps/api/tests/test_geocodage.py) — consommation Nominatim
Tous les appels réseau sont **mockés** avec `@patch("apps.api.views.requests.get")`
— les tests ne dépendent **jamais** d'Internet ni de Nominatim.
- `test_geocodage_enregistre_les_coordonnees` : réponse mockée → coordonnées
  enregistrées, et **vérifie la présence de l'en-tête `User-Agent`**.
- `test_geocodage_arrondit_la_precision_excessive_de_nominatim` : entrée à 14
  décimales → stockée arrondie à 6 (protège de `numeric field overflow`).
- `test_geocodage_adresse_introuvable` : liste vide → **404**.
- `test_geocodage_reserve_au_cure` : un Secrétaire → **403**.
- `test_geocodage_inverse_est_public_et_renvoie_l_adresse` : décompose la réponse
  OSM en avenue/quartier/commune/ville.
- `test_geocodage_inverse_adresse_introuvable` : `error` dans la réponse → 404.
- `test_geocodage_inverse_exige_lat_et_lon` : sans paramètres → 400.
- `test_recherche_adresse_combine_les_champs_dans_la_requete` : vérifie que les 4
  champs sont bien concaténés dans le paramètre `q` envoyé à Nominatim.
- `test_recherche_adresse_exige_au_moins_un_champ` : requête vide → 400.
- `test_recherche_adresse_sans_resultat` : liste vide → 200 avec `resultats: []`.

---

## Questions probables du jury & réponses

**1. Quelle est la différence entre « créer » et « consommer » une API REST ?**
Créer une API = j'expose mes propres ressources (paroissiens, dons…) via des
endpoints HTTP que d'autres appellent (mes 5 ViewSets DRF). Consommer une API =
c'est mon serveur qui appelle une **API tierce** (Nominatim) avec la librairie
`requests`, et j'exploite sa réponse. Le brief exige explicitement les deux
(§8a et §8b), et l'app `api` fait les deux.

**2. Comment sécurisez-vous l'API ?**
Trois couches. (a) **Authentification JWT** : sans un jeton d'accès valide dans
`Authorization: Bearer`, tout endpoint protégé renvoie 401 (`IsAuthenticated`
par défaut). (b) **Autorisation par rôle** : `creer_permission_role` distingue
lecture et écriture selon le groupe Django (Curé / Secrétaire / Trésorier /
Lecteur). (c) **Isolation multi-tenant** : chaque queryset est refiltré sur la
paroisse de l'utilisateur. Plus le HTTPS et les secrets en variables
d'environnement au déploiement.

**3. Comment un utilisateur d'une paroisse ne voit-il pas les données d'une autre
via l'API ?**
`IsolationParoisseMixin.get_queryset` fait `queryset.filter(paroisse=
request.user.paroisse)`. Un objet d'une autre paroisse n'entre jamais dans le
queryset : la liste ne le montre pas, et son détail renvoie 404. En écriture,
`perform_create` **impose** la paroisse de l'utilisateur, donc on ne peut pas
créer « pour » une autre paroisse même en falsifiant le corps de la requête. Deux
tests le prouvent dans `test_isolation_api.py`.

**4. Pourquoi refiltrer dans le mixin alors qu'il existe déjà un manager
multi-tenant automatique ?**
Le manager automatique dépend d'une `ContextVar` positionnée par un middleware
Django. Ce middleware s'exécute **avant** l'authentification JWT de DRF (qui n'a
lieu que dans `APIView.dispatch()`). Pour une requête authentifiée uniquement par
jeton (sans cookie de session), la `ContextVar` ne serait donc pas fiable. Le
mixin ne fait pas confiance à ce mécanisme et filtre explicitement sur
`request.user.paroisse` : c'est un choix de sécurité délibéré, documenté dans la
docstring.

**5. Comment fonctionne l'authentification JWT concrètement ?**
Le client envoie identifiant + mot de passe à `POST /api/jeton/`. S'ils sont
valides (et la paroisse active), il reçoit un **access** (30 min) et un
**refresh** (1 jour). Il joint ensuite `Authorization: Bearer <access>` à chaque
requête. Quand l'access expire, il obtient un nouveau couple via
`POST /api/jeton/rafraichir/` (avec rotation du refresh). Aucun mot de passe ne
circule après la première requête, et le serveur ne stocke pas de session.

**6. Le reçu fiscal est-il vraiment créé dans la même transaction, même via
l'API ?**
Oui. `DonViewSet.perform_create` ne fait pas un simple `save` : il appelle le
service `enregistrer_don_avec_recu`, décoré `@transaction.atomic`, qui crée le
`Don` **et** son `RecuFiscal` ensemble. Si la création du reçu échoue, le don est
annulé (rollback). C'est la **même fonction** que celle utilisée par l'interface
web : la règle métier n'est pas dupliquée. Le test
`test_creer_un_don_via_l_api_genere_aussi_le_recu_fiscal` le vérifie.

**7. Comment gérez-vous la pagination et le filtrage ?**
Pagination globale `PageNumberPagination`, 20 objets par page : les réponses de
liste ont la forme `{count, next, previous, results}`. Le filtrage repose sur
`DjangoFilterBackend` branché globalement dans `REST_FRAMEWORK`, ce qui permet de
filtrer par paramètres d'URL sans code supplémentaire dans les vues.

**8. Pourquoi le géocodage de la paroisse est-il réservé au Curé, alors que la
recherche d'adresse est publique ?**
Modifier la localisation **officielle** de la paroisse est une décision
administrative : `GeocoderParoisseView` utilise `creer_permission_role()` sans
rôle, donc seuls Curé/superuser passent. À l'inverse, `GeocoderInverseView` et
`RechercherAdresseView` servent la **page de souscription**, avant même qu'un
compte existe : elles doivent être `AllowAny`, sinon personne ne pourrait
s'inscrire.

**9. Vos tests dépendent-ils du réseau ou de Nominatim ?**
Non. Tous les appels à Nominatim sont **mockés** via
`@patch("apps.api.views.requests.get")`. Les tests contrôlent la fausse réponse
et vérifient notre traitement (arrondi à 6 décimales, présence du `User-Agent`,
codes 404/503, décomposition de l'adresse). Ils sont donc rapides et
déterministes.

**10. Que se passe-t-il si une paroisse est suspendue mais qu'un jeton a déjà été
émis ?**
Le sérialiseur JWT bloque l'**émission** d'un nouveau jeton. Mais un jeton déjà
en circulation reste techniquement valide jusqu'à expiration — c'est pourquoi la
classe de permission revérifie `paroisse.est_active` à **chaque** requête et
renvoie 403 le cas échéant. Le test `test_jeton_deja_emis_refuse_apres_suspension`
couvre précisément ce scénario.
