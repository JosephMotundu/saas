# App `communication` — fiche de révision

> Fiche de défense pour la soutenance. Objectif : pouvoir expliquer chaque
> ligne de l'app `communication` au jury, en citant le vrai code.

## Rôle de l'application

L'app `communication` correspond à l'app Django `communication` du brief (§5) et
à l'étape 8 du plan de construction. Elle gère **les annonces paroissiales** : un
secrétariat rédige des communiqués internes (destinés à un groupe de la paroisse
ou à toute la paroisse) et peut, en cochant une case, en publier certains sur une
**page publique consultable sans compte**.

Son originalité par rapport aux autres apps métier : elle expose **deux surfaces**
distinctes.

1. Une surface **interne** (CRUD authentifié, réservé au personnel) — [`urls.py`](../apps/communication/urls.py).
2. Une surface **publique** (lecture seule, un visiteur anonyme) — [`urls_publiques.py`](../apps/communication/urls_publiques.py).

C'est le point le plus « défendable » de l'app, à savoir l'articuler clairement.

---

## Critères du jury démontrés ici

| Critère (§3 du brief) | Où le montrer dans cette app |
|---|---|
| 1. BDD relationnelle, FK, contraintes | [`models.py`](../apps/communication/models.py) : `Annonce` avec 3 FK (`auteur`, `groupe_cible`, `paroisse`), `NOT NULL` par défaut, `null=True` sur `groupe_cible`. |
| 1. CRUD complet | [`views.py`](../apps/communication/views.py) : `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`. |
| 6. Architecture MVT | Model (`Annonce`) / Template (`templates/communication/`) / View (vues génériques). Séparation stricte. |
| 7. Rôles et permissions | `roles_autorises` + `RoleRequisMixin` : lecture = Secrétaire/Lecteur, écriture = Secrétaire (+ Curé/superadmin toujours). |
| 4 / multi-tenant (§4) | `FiltrageParoisseMixin` + manager `creer_manager_paroisse()` + isolation de la page publique par `slug`. |
| Page publique / déploiement | `AnnoncePubliqueListView` accessible sans authentification, une URL par paroisse. |
| 11. Tests unitaires | [`tests/`](../apps/communication/tests/) : modèle, vues internes, page publique (12 tests). |
| 15. Backoffice admin | [`admin.py`](../apps/communication/admin.py) : `list_display`, `list_filter`, `search_fields`. |
| 14. Optimisation requêtes | `select_related` dans les vues et `list_select_related` dans l'admin. |

---

## `models.py` — le modèle `Annonce`

Chemin : [`apps/communication/models.py`](../apps/communication/models.py)
Rôle : définir l'unique entité de l'app et son isolation multi-tenant.

```python
class Annonce(models.Model):
    titre = models.CharField("titre", max_length=200)
    contenu = models.TextField("contenu")
    date_publication = models.DateField("date de publication")
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="auteur",
        related_name="annonces",
        on_delete=models.PROTECT,
    )
    groupe_cible = models.ForeignKey(
        Group,
        verbose_name="groupe cible",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Laisser vide pour une annonce visible de toute la paroisse.",
    )
    publique = models.BooleanField(
        "visible publiquement",
        default=False,
        help_text="Affichée sur la page publique de la paroisse, consultable sans compte.",
    )
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="annonces", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()
```

Points à défendre champ par champ :

- **`titre` / `contenu` / `date_publication`** : les données métier de base. Aucun
  `null=True`, donc `NOT NULL` en base — contrainte d'intégrité (critère 1).
- **`auteur`** : FK vers le modèle utilisateur custom (`settings.AUTH_USER_MODEL`,
  pas `User` en dur — bonne pratique Django). `on_delete=models.PROTECT` :
  **on ne peut pas supprimer un utilisateur qui a signé des annonces** ; cela
  protège l'intégrité de l'historique. `related_name="annonces"` permet
  `utilisateur.annonces.all()`.
- **`groupe_cible`** : FK vers `django.contrib.auth.models.Group` — on réutilise
  les **groupes Django** qui portent déjà les rôles (Curé, Secrétaire, Trésorier,
  Lecteur). `null=True, blank=True` : le champ est facultatif ; vide = annonce
  destinée à **toute la paroisse** (voir le `help_text`). `on_delete=SET_NULL` :
  si un groupe disparaît, l'annonce n'est pas détruite, son ciblage retombe
  simplement sur « toute la paroisse ». C'est une relation **1:N** (un groupe → N
  annonces).
- **`publique`** : booléen, `default=False`. C'est le **commutateur** qui décide
  si l'annonce sort sur la page publique. Par défaut une annonce reste interne —
  la publication est un acte explicite, pas un oubli.
- **`paroisse`** : FK vers le tenant (`Paroisse`). Présente sur **toutes** les
  entités métier (§4). `PROTECT` empêche de supprimer une paroisse qui a encore
  des annonces.

Éléments transverses :

- **`objects = creer_manager_paroisse()`** : remplace le manager par défaut par le
  **manager multi-tenant** ([`apps/comptes/managers.py`](../apps/comptes/managers.py)).
  Son `get_queryset()` filtre automatiquement sur la paroisse courante (posée dans
  une `ContextVar` par le middleware). C'est le **filet de sécurité** qui protège
  y compris le Django Admin. Hors requête (migrations, shell, tests appelant les
  modèles directement), aucun filtrage n'est appliqué.
- **`Meta.ordering = ["-date_publication"]`** : les annonces les plus récentes en
  premier, partout, sans avoir à le répéter dans chaque vue.
- **`__str__`** : renvoie le titre — lisible dans l'admin et les logs.
- **`get_absolute_url()`** : renvoie l'URL de détail interne
  (`reverse("communication:annonce_detail", ...)`). Utilisé par `CreateView`/
  `UpdateView` comme redirection après enregistrement quand aucun `success_url`
  n'est fixé.

Formes normales (critère 1) : chaque attribut dépend de la clé (l'id de
l'annonce) ; le groupe et la paroisse sont des entités séparées référencées par
FK plutôt que dupliquées → 1FN et 2FN respectées.

---

## `forms.py` — le formulaire de saisie

Chemin : [`apps/communication/forms.py`](../apps/communication/forms.py)
Rôle : formulaire de création/édition d'une annonce.

```python
class AnnonceForm(forms.ModelForm):
    class Meta:
        model = Annonce
        fields = ["titre", "contenu", "date_publication", "groupe_cible", "publique"]
        widgets = {"date_publication": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groupe_cible"].queryset = Group.objects.all()
        self.fields["groupe_cible"].required = False
```

À défendre :

- **`fields` n'inclut ni `auteur` ni `paroisse`** : ces deux champs ne sont **pas**
  saisis par l'utilisateur. Ils sont posés automatiquement côté serveur (l'auteur
  = l'utilisateur connecté ; la paroisse = la paroisse courante). C'est une mesure
  de **sécurité** : un utilisateur ne peut pas usurper un auteur ni attribuer une
  annonce à une autre paroisse en trafiquant le formulaire.
- **`widget` `type="date"`** : affiche un vrai sélecteur de date HTML5.
- **`__init__`** : le champ `groupe_cible` est rendu **facultatif** (`required =
  False`) — cohérent avec `null=True, blank=True` du modèle — et sa liste de choix
  est explicitement fixée à tous les groupes.

---

## `views.py` — les vues (le « contrôleur » MVT)

Chemin : [`apps/communication/views.py`](../apps/communication/views.py)
Rôle : toute la logique de présentation, interne **et** publique.

### Constantes de rôles

```python
ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)
```

- Consulter les annonces : **Secrétaire** ou **Lecteur**.
- Créer / modifier / supprimer : **Secrétaire** uniquement.
- Le **Curé** et le **superadmin** passent toujours (ils sont autorisés dans
  `RoleRequisMixin.test_func`, pas besoin de les lister ici). C'est fidèle au §7
  du brief : « Curé : accès complet à sa paroisse ».

### Garde de module (fonction `_verifier_module_communication`)

```python
def _verifier_module_communication(paroisse):
    abonnement = getattr(paroisse, "abonnement", None)
    if abonnement is not None and not abonnement.module_autorise("communication"):
        raise Http404("Module communication non inclus dans l'offre de cette paroisse.")
```

Utilisée **par la surface publique**. Si l'offre d'une paroisse n'inclut plus le
module communication, sa page publique renvoie 404 : l'espace public est une
**conséquence** du module payant, pas un droit acquis indépendant. Côté interne,
c'est le mixin `ModuleAutoriseMixin` qui joue ce rôle.

### Les cinq vues internes (CRUD)

Toutes combinent les mêmes mixins, dans cet ordre :
`RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, <vue générique>`.

| Vue | URL name | Rôle | Détail |
|---|---|---|---|
| `AnnonceListView` | `annonce_liste` | lecture | liste paginée (25/page), `select_related("auteur", "groupe_cible")` |
| `AnnonceDetailView` | `annonce_detail` | lecture | fiche d'une annonce |
| `AnnonceCreateView` | `annonce_creer` | écriture | pose `auteur = request.user`, message « Annonce publiée. » |
| `AnnonceUpdateView` | `annonce_modifier` | écriture | message « Modifications enregistrées. » |
| `AnnonceDeleteView` | `annonce_supprimer` | écriture | confirmation, message « Annonce supprimée. », `success_url` = liste |

Rôle de chaque mixin (définis dans [`apps/comptes/mixins.py`](../apps/comptes/mixins.py)) :

- **`RoleRequisMixin`** (hérite de `LoginRequiredMixin` + `UserPassesTestMixin`) :
  impose l'authentification puis vérifie l'appartenance à un des `roles_autorises`
  (superadmin et Curé toujours OK). Un échec renvoie **403**.
- **`ModuleAutoriseMixin`** : bloque si le module `communication` n'est pas dans
  l'offre de la paroisse (redirige vers le tableau de bord avec un message). Ne
  bloque jamais le superadmin ni une paroisse sans abonnement.
- **`FiltrageParoisseMixin`** (hérite de `LoginRequiredMixin`) : filtre le queryset
  sur `request.paroisse` (**défense en profondeur** redondante avec le manager) et,
  dans `form_valid`, **rattache l'objet créé à la paroisse courante**
  (`form.instance.paroisse = self.request.paroisse`). C'est pour cela que le
  formulaire n'a pas besoin du champ `paroisse`.

Focus sur la création :

```python
class AnnonceCreateView(RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, CreateView):
    ...
    def form_valid(self, form):
        form.instance.auteur = self.request.user
        messages.success(self.request, "Annonce publiée.")
        return super().form_valid(form)
```

L'`auteur` est fixé ici (utilisateur connecté), la `paroisse` est fixée par le
mixin parent. `super().form_valid()` appelle en cascade le mixin qui pose la
paroisse — l'ordre des mixins compte.

### Les deux vues publiques (lecture seule, sans authentification)

```python
class AnnoncePubliqueListView(ListView):
    template_name = "communication/annonces_publiques.html"
    paginate_by = 20

    def get_paroisse(self):
        paroisse = get_object_or_404(Paroisse, slug=self.kwargs["slug"], est_active=True)
        _verifier_module_communication(paroisse)
        return paroisse

    def get_queryset(self):
        self.paroisse = self.get_paroisse()
        return Annonce.objects.filter(paroisse=self.paroisse, publique=True).order_by(
            "-date_publication"
        )
```

Points cruciaux à défendre :

- **Aucun mixin d'authentification** : n'importe quel visiteur peut accéder à la
  page. C'est voulu — c'est la vitrine publique.
- **Isolation par `slug`** (et non par middleware) : ici il n'y a pas
  d'utilisateur connecté, donc pas de « paroisse courante » posée par le
  middleware. La paroisse est identifiée par le **slug dans l'URL**
  (`/paroisses/saint-raphael/annonces/`). `get_object_or_404(..., est_active=True)`
  garantit qu'une **paroisse suspendue/inactive** renvoie 404.
- **`publique=True` en dur** dans le filtre : seules les annonces explicitement
  publiées sortent. Les communiqués internes restent invisibles.
- **Filtrage explicite `paroisse=self.paroisse`** : impossible de voir les
  annonces d'une autre paroisse via ce slug.
- `AnnoncePubliqueDetailView` applique **exactement les mêmes garde-fous** dans son
  `get_queryset()` : une annonce non publique (ou d'une autre paroisse, ou d'une
  paroisse suspendue) donne un **404** au visiteur — jamais une fuite.

---

## `urls.py` vs `urls_publiques.py` — pourquoi DEUX fichiers d'URLs ?

C'est **le** point structurant de l'app. Les deux fichiers décrivent deux mondes
différents, montés à deux préfixes différents dans [`config/urls.py`](../config/urls.py).

### `urls.py` — surface interne

Chemin : [`apps/communication/urls.py`](../apps/communication/urls.py)
Monté sous `communication/` (ligne 18 de `config/urls.py`).
Namespace : `app_name = "communication"`.

```python
urlpatterns = [
    path("", views.AnnonceListView.as_view(), name="annonce_liste"),
    path("nouvelle/", views.AnnonceCreateView.as_view(), name="annonce_creer"),
    path("<int:pk>/", views.AnnonceDetailView.as_view(), name="annonce_detail"),
    path("<int:pk>/modifier/", views.AnnonceUpdateView.as_view(), name="annonce_modifier"),
    path("<int:pk>/supprimer/", views.AnnonceDeleteView.as_view(), name="annonce_supprimer"),
]
```

- URLs du type `/communication/`, `/communication/nouvelle/`, `/communication/3/`.
- **Pas de slug de paroisse dans l'URL** : la paroisse est déduite de
  l'utilisateur connecté (middleware → `request.paroisse`). Un secrétaire ne voit
  que **sa** paroisse, sans jamais la nommer dans l'URL.
- Réservé au personnel authentifié.

### `urls_publiques.py` — surface publique

Chemin : [`apps/communication/urls_publiques.py`](../apps/communication/urls_publiques.py)
Monté sous `paroisses/<slug:slug>/` (ligne 21 de `config/urls.py`).
Namespace : `app_name = "communication_publique"`.

```python
urlpatterns = [
    path("annonces/", AnnoncePubliqueListView.as_view(), name="annonce_liste"),
    path("annonces/<int:pk>/", AnnoncePubliqueDetailView.as_view(), name="annonce_detail"),
]
```

- URLs du type `/paroisses/saint-raphael/annonces/` et
  `/paroisses/saint-raphael/annonces/3/`.
- **Le `slug` de la paroisse EST dans l'URL** (capturé par le préfixe
  `<slug:slug>` de `config/urls.py`). C'est ce qui identifie le tenant en
  l'absence d'utilisateur connecté.
- Accessible sans compte.

### Résumé de la distinction (à réciter)

| | Interne (`urls.py`) | Publique (`urls_publiques.py`) |
|---|---|---|
| Préfixe | `communication/` | `paroisses/<slug>/` |
| Namespace | `communication` | `communication_publique` |
| Authentification | Obligatoire | Aucune |
| Identification du tenant | `request.paroisse` (middleware) | `slug` dans l'URL |
| Opérations | CRUD complet | Lecture seule |
| Filtre annonces | toutes celles de la paroisse | uniquement `publique=True` |
| Mixins | RoleRequis + Module + Filtrage | aucun (garde-fous en dur dans `get_queryset`) |

Pourquoi séparer plutôt que tout mettre dans un seul fichier ? Parce que les deux
surfaces ont des **règles d'accès opposées** (auth obligatoire vs anonyme) et des
**mécanismes d'isolation différents** (middleware vs slug). Deux fichiers + deux
namespaces rendent la frontière **explicite et impossible à confondre** : impossible
qu'une URL interne « fuite » accidentellement dans l'espace public.

---

## `apps.py`

Chemin : [`apps/communication/apps.py`](../apps/communication/apps.py)
Configuration standard de l'app. Notable : `label = "communication"` et
`name = "apps.communication"` (les apps vivent dans le paquet `apps/`), plus un
`verbose_name = "Communication"` pour l'admin.

---

## `admin.py` — le backoffice (critère 15)

Chemin : [`apps/communication/admin.py`](../apps/communication/admin.py)

```python
@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ("titre", "date_publication", "auteur", "groupe_cible", "paroisse")
    list_filter = ("paroisse", "groupe_cible", "date_publication")
    search_fields = ("titre", "contenu")
    list_select_related = ("auteur", "groupe_cible", "paroisse")
```

- **`list_display`** : colonnes de la liste (critère 15).
- **`list_filter`** : filtres latéraux par paroisse, groupe, date.
- **`search_fields`** : recherche plein texte sur titre et contenu.
- **`list_select_related`** : joint auteur/groupe/paroisse en une requête —
  évite le problème des **N+1 requêtes** (critère 14, optimisation).
- L'admin hérite en plus de l'isolation par paroisse via le **manager par défaut**
  du modèle (`get_queryset()` de l'admin utilise `Annonce.objects`), donc le
  backoffice est aussi « scellé par paroisse » (critère 15).

---

## Templates

Dossier : [`apps/communication/templates/communication/`](../apps/communication/templates/communication/)

Deux familles, correspondant aux deux surfaces. Les templates **internes**
étendent `base_app.html` (interface d'administration authentifiée) ; les
templates **publics** étendent `base_public.html` (vitrine).

| Template | Surface | Rôle |
|---|---|---|
| `annonce_liste.html` | interne | Tableau des annonces (titre, date, destinataires, auteur, étiquette « Publique »), pagination, état vide « Aucune annonce pour l'instant. Publiez la première. ». Affiche aussi le **lien vers la page publique** (`request.paroisse.slug`) à copier. |
| `annonce_detail.html` | interne | Fiche d'une annonce + actions Modifier / Supprimer. |
| `annonce_form.html` | interne | Formulaire création/édition (réutilise le partial `partials/_form_field.html`). Titre « Publier » ou « Modifier » selon `object`. |
| `annonce_confirmer_suppression.html` | interne | Page de confirmation avant suppression (POST + CSRF). |
| `annonces_publiques.html` | publique | Liste des communiqués publics d'une paroisse, en cartes (`base_public.html`), avec nom/ville/diocèse, pagination, état vide « Aucun communiqué public pour l'instant. ». |
| `annonce_publique_detail.html` | publique | Détail d'un communiqué public + lien retour vers tous les communiqués de la paroisse. |

Les templates ne contiennent **aucune logique métier** (juste de l'affichage
conditionnel) — la séparation MVT est respectée (critère 6). Le ton des libellés
suit la direction artistique du brief (« Publier une annonce », états vides
invitant à agir).

---

## Tests

Dossier : [`apps/communication/tests/`](../apps/communication/tests/) — 12 tests répartis en 3 fichiers.

### [`test_models.py`](../apps/communication/tests/test_models.py) — le modèle

- **`test_creation_annonce`** : crée une paroisse, un auteur, une annonce ;
  vérifie que la PK est posée, que `str(annonce)` renvoie le titre, et que
  `groupe_cible` vaut `None` par défaut (annonce « toute la paroisse »).

### [`test_vues.py`](../apps/communication/tests/test_vues.py) — surface interne (rôles + isolation)

- **`test_secretaire_peut_publier_une_annonce`** : un Secrétaire POST le formulaire
  de création → redirection 302, l'annonce existe, son `auteur` est bien le
  secrétaire et sa `paroisse` la bonne (preuve que `auteur`/`paroisse` sont posés
  serveur, pas saisis).
- **`test_lecteur_ne_peut_pas_publier_une_annonce`** : un Lecteur qui tente
  d'accéder à la création reçoit **403** (rôle insuffisant → critère 7).
- **`test_isolation_multi_tenant_sur_les_annonces`** : une annonce d'une **autre**
  paroisse n'apparaît **pas** dans la liste vue par le secrétaire (critère §4).

### [`test_page_publique.py`](../apps/communication/tests/test_page_publique.py) — surface publique

- **`test_paroisse_recoit_un_slug_automatiquement`** : « Saint Raphaël » →
  slug `saint-raphael` (base du routage public).
- **`test_deux_paroisses_de_nom_proche_ont_des_slugs_distincts`** : « Saint
  Pierre » et « Saint-Pierre » obtiennent des slugs différents (unicité).
- **`test_page_publique_accessible_sans_authentification`** : un client **anonyme**
  obtient 200 et voit une annonce `publique=True`.
- **`test_page_publique_cache_les_annonces_non_publiques`** : une annonce
  `publique=False` n'apparaît **pas** sur la liste publique.
- **`test_annonce_non_publique_404_pour_un_invite`** : accéder au détail public
  d'une annonce non publique renvoie **404** (pas de fuite par URL directe).
- **`test_page_publique_404_si_paroisse_suspendue`** : `est_active=False` → la page
  publique renvoie 404 (une paroisse suspendue perd sa vitrine).
- **`test_page_publique_isolee_par_paroisse`** : l'annonce publique d'une autre
  paroisse n'apparaît pas sous le slug courant (isolation).
- **`test_pied_de_page_affiche_le_nom_de_la_paroisse_sur_la_page_publique`** :
  contexte `paroisse` bien transmis au template public.
- **`test_pied_de_page_ne_montre_aucune_paroisse_pour_un_visiteur_anonyme`** : sur
  la page d'accueil générale (`core:accueil`), on voit « ParoisseConnect » mais
  pas « Saint Raphaël » (pas de tenant hors contexte).
- **`test_secretaire_peut_marquer_une_annonce_publique`** : POST avec
  `"publique": "on"` → l'annonce créée a bien `publique is True`.

Ce que la suite couvre au total : le modèle, les **permissions par rôle**,
**l'isolation multi-tenant côté interne ET côté public**, la suspension de
paroisse, et le commutateur `publique`.

---

## Questions probables du jury & réponses

**Q1. Pourquoi deux fichiers d'URLs pour une seule app ?**
Parce qu'il y a deux surfaces avec des règles opposées. `urls.py` (namespace
`communication`) sert le CRUD interne authentifié, monté sous `communication/`, où
la paroisse est déduite de l'utilisateur connecté. `urls_publiques.py` (namespace
`communication_publique`) sert la vitrine anonyme, montée sous
`paroisses/<slug:slug>/`, où la paroisse est identifiée par le slug de l'URL.
Séparer rend la frontière de sécurité explicite.

**Q2. Sur la page publique il n'y a pas d'utilisateur connecté — comment savez-vous
de quelle paroisse afficher les annonces ?**
Par le **slug** capturé dans l'URL (`config/urls.py` : `paroisses/<slug:slug>/`).
La vue fait `get_object_or_404(Paroisse, slug=self.kwargs["slug"], est_active=True)`.
Le middleware multi-tenant, lui, ne sert que la surface interne (il s'appuie sur
l'utilisateur connecté).

**Q3. Comment garantissez-vous qu'une annonce interne ne fuit pas sur la page
publique ?**
Trois protections cumulées : le champ `publique` vaut `False` par défaut (rien
n'est public par accident) ; les deux vues publiques filtrent en dur
`publique=True` dans leur `get_queryset()` ; et le test
`test_page_publique_cache_les_annonces_non_publiques` +
`test_annonce_non_publique_404_pour_un_invite` le vérifient (liste ET détail).

**Q4. Qui peut publier une annonce ? Et le Curé ?**
Écriture (créer/modifier/supprimer) = **Secrétaire** (`ROLES_ECRITURE`). Lecture =
Secrétaire + Lecteur (`ROLES_LECTURE`). Le **Curé** et le **superadmin** sont
autorisés partout : c'est codé dans `RoleRequisMixin.test_func`, donc inutile de
les répéter dans chaque vue. C'est conforme au §7 : « Curé : accès complet ».

**Q5. Pourquoi `auteur` et `paroisse` ne sont-ils pas dans le formulaire ?**
Sécurité. Les inclure permettrait à un utilisateur de forger une requête pour
usurper un auteur ou attribuer une annonce à une autre paroisse. L'`auteur` est
posé dans `AnnonceCreateView.form_valid` (`= request.user`) et la `paroisse` par
`FiltrageParoisseMixin.form_valid` (`= request.paroisse`).

**Q6. Comment l'isolation multi-tenant est-elle assurée côté interne ?**
Deux niveaux. Le **manager par défaut** `creer_manager_paroisse()` filtre
automatiquement sur la paroisse courante (défense de fond, qui protège aussi
l'admin). Et le `FiltrageParoisseMixin` refiltre explicitement sur
`request.paroisse` dans chaque vue — défense en profondeur. Le test
`test_isolation_multi_tenant_sur_les_annonces` le prouve.

**Q7. Que se passe-t-il si une paroisse est suspendue ou n'a plus le module
communication ?**
Suspension : `get_object_or_404(..., est_active=True)` → la page publique renvoie
404 (`test_page_publique_404_si_paroisse_suspendue`). Module retiré :
`_verifier_module_communication` lève `Http404` côté public, et
`ModuleAutoriseMixin` bloque côté interne. La page publique est une conséquence du
module payant, pas un droit acquis.

**Q8. Pourquoi `on_delete=PROTECT` sur `auteur` et `paroisse`, mais `SET_NULL` sur
`groupe_cible` ?**
`PROTECT` interdit de supprimer un utilisateur ou une paroisse tant qu'il reste des
annonces — on préserve l'intégrité de l'historique. `SET_NULL` sur `groupe_cible`
est plus souple : si un groupe disparaît, l'annonce survit et retombe simplement
sur « toute la paroisse » (cohérent avec `null=True`).

**Q9. Où est le CRUD complet exigé par le critère 1 ?**
Dans `views.py` : `AnnonceCreateView` (Create), `AnnonceListView`/
`AnnonceDetailView` (Read), `AnnonceUpdateView` (Update), `AnnonceDeleteView`
(Delete) — les cinq vues génériques de Django, chacune avec son URL et son
template.

**Q10. Comment évitez-vous le problème des N+1 requêtes sur la liste ?**
`AnnonceListView.get_queryset()` ajoute `select_related("auteur", "groupe_cible")`
pour joindre en une seule requête SQL les objets affichés dans chaque ligne du
tableau. L'admin fait de même avec `list_select_related` (critère 14).
