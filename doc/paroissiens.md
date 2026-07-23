# App `paroissiens` — fiche de révision pour la soutenance

> Fiche de défense de l'application Django `paroissiens` du SaaS **ParoisseConnect**.
> Tout ce qui est écrit ici est **ancré dans le code réel** ; les liens pointent vers
> les fichiers sources pour montrer au jury exactement où se trouve chaque élément.

## Rôle de l'application

L'app `paroissiens` gère le **répertoire des personnes** de la paroisse : les
**familles** et les **paroissiens** (fidèles). C'est l'annuaire central sur lequel
s'appuient les autres apps (sacrements, célébrations, finances) : un baptême, un don
ou une intention de messe se rattachent à un `Paroissien` défini ici.

Elle expose un **CRUD complet** (lister, consulter, créer, modifier, supprimer) pour
deux entités reliées par une relation **1:N** (une famille compte plusieurs membres),
le tout **isolé par paroisse** (multi-tenant) et **protégé par rôle**.

Fichiers de l'app :

- [models.py](../apps/paroissiens/models.py) — les modèles `Famille` et `Paroissien`
- [forms.py](../apps/paroissiens/forms.py) — les formulaires `FamilleForm` et `ParoissienForm`
- [views.py](../apps/paroissiens/views.py) — les 10 vues CRUD (générique Django)
- [urls.py](../apps/paroissiens/urls.py) — le routage
- [admin.py](../apps/paroissiens/admin.py) — le backoffice Django Admin
- [apps.py](../apps/paroissiens/apps.py) — la configuration de l'app
- [migrations/0001_initial.py](../apps/paroissiens/migrations/0001_initial.py) — le schéma SQL généré
- [tests/test_models.py](../apps/paroissiens/tests/test_models.py) et [tests/test_vues.py](../apps/paroissiens/tests/test_vues.py) — les tests
- `templates/paroissiens/` — 8 templates server-rendered

---

## Critères du jury démontrés ici

| Critère (§3 du brief) | Où le montrer dans cette app |
|---|---|
| **1. BDD relationnelle** (1:N, FK, FK nullable, contraintes) | [models.py](../apps/paroissiens/models.py) : `Famille` → `Paroissien` en 1:N ; `famille` est une FK **nullable** (`null=True`), `paroisse` une FK **non nullable** protégée |
| **2. Langage backend** | Python 3.12 / Django 5 dans tous les fichiers |
| **5. Responsive design** | 8 templates étendent `base_app.html`, tables `.table-registre` et grilles responsives (thème custom) |
| **6. Architecture MVT** | Séparation stricte : `models.py` (M), `templates/` (V=template), `views.py` (V=view/contrôleur) ; aucune logique métier dans les templates |
| **7. Rôles et permissions** | `RoleRequisMixin` + constantes `ROLES_LECTURE` / `ROLES_ECRITURE` dans [views.py](../apps/paroissiens/views.py) |
| **9. POO** | Méthodes métier `nom_complet()`, `__str__()`, `get_absolute_url()` sur les modèles ; vues fondées sur l'héritage de classes (`CreateView`, etc.) et mixins |
| **11. Tests unitaires** | [tests/test_models.py](../apps/paroissiens/tests/test_models.py) (modèles) + [tests/test_vues.py](../apps/paroissiens/tests/test_vues.py) (permissions, isolation) |
| **14. Jointures optimisées** | `select_related("famille")` sur la liste, `prefetch_related("membres")` sur le détail famille |
| **15. Backoffice admin** | [admin.py](../apps/paroissiens/admin.py) : `list_display`, `search_fields`, `list_filter`, `autocomplete_fields`, `list_select_related` |
| **Multi-tenant (§4)** | Double filtrage : manager par défaut (`creer_manager_paroisse`) + `FiltrageParoisseMixin` sur chaque vue |

---

## [models.py](../apps/paroissiens/models.py) — le cœur relationnel

Deux modèles. Ils importent le **manager multi-tenant** partagé et le modèle
`Paroisse` (le tenant) :

```python
from apps.comptes.managers import creer_manager_paroisse
from apps.comptes.models import Paroisse
```

### Modèle `Famille`

```python
class Famille(models.Model):
    nom = models.CharField("nom de famille", max_length=200)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="familles", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "famille"
        verbose_name_plural = "familles"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse("paroissiens:famille_detail", args=[self.pk])
```

Points à défendre :

- **FK `paroisse` obligatoire** (pas de `null=True`) : toute famille appartient à une
  paroisse — c'est le pilier de l'isolation multi-tenant. `on_delete=models.PROTECT`
  interdit de supprimer une paroisse qui contient encore des familles (**contrainte
  d'intégrité référentielle**).
- **`related_name="familles"`** : côté `Paroisse`, on accède aux familles par
  `paroisse.familles.all()`.
- **`objects = creer_manager_paroisse()`** : remplace le manager par défaut par un
  manager qui **filtre automatiquement** sur la paroisse courante (voir plus bas).
- **`ordering = ["nom"]`** : tri alphabétique par défaut, cohérent avec un annuaire.
- **`get_absolute_url()`** : après création/édition, Django redirige tout seul vers la
  fiche de la famille (méthode métier, POO).

### Modèle `Paroissien`

```python
class Paroissien(models.Model):
    SEXE_CHOICES = [
        ("M", "Masculin"),
        ("F", "Féminin"),
    ]

    nom = models.CharField("nom", max_length=100)
    prenom = models.CharField("prénom", max_length=100)
    sexe = models.CharField("sexe", max_length=1, choices=SEXE_CHOICES)
    date_naissance = models.DateField("date de naissance", null=True, blank=True)
    adresse = models.CharField("adresse", max_length=255, blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    photo = models.ImageField("photo", upload_to="paroissiens/", blank=True, null=True)
    famille = models.ForeignKey(
        Famille,
        verbose_name="famille",
        related_name="membres",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="paroissiens", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()

    class Meta:
        verbose_name = "paroissien"
        verbose_name_plural = "paroissiens"
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def get_absolute_url(self):
        return reverse("paroissiens:paroissien_detail", args=[self.pk])
```

Points à défendre :

- **`sexe` avec `choices`** : contrainte de domaine (seulement `M`/`F`) ; dans les
  templates on affiche le libellé lisible via `get_sexe_display` (méthode générée
  automatiquement par Django à partir des `choices`).
- **`date_naissance` nullable** (`null=True, blank=True`) : une date de naissance peut
  être inconnue à l'enregistrement. `null=True` = la colonne SQL accepte NULL ;
  `blank=True` = le champ n'est pas obligatoire dans les formulaires.
- **`photo = ImageField(upload_to="paroissiens/")`** : gestion des **médias**. Les
  fichiers uploadés sont rangés dans `MEDIA_ROOT/paroissiens/`. `ImageField` valide
  au passage que le fichier est bien une image (nécessite Pillow).
- **`famille` = FK NULLABLE avec `on_delete=models.SET_NULL`** : c'est le point clé de
  la relation 1:N. Un paroissien **peut** ne pas avoir de famille (`null=True`). Et si
  on supprime la famille, les membres ne sont **pas** supprimés : leur champ `famille`
  repasse simplement à `NULL` (`SET_NULL`). C'est exactement ce que teste
  `test_suppression_famille_detache_les_paroissiens_sans_les_supprimer`.
- **`related_name="membres"`** : côté `Famille`, on liste ses membres avec
  `famille.membres.all()` — utilisé dans le template `famille_detail.html`.
- **Méthodes métier `nom_complet()` et `__str__()`** (critère POO) : centralisent
  l'affichage « Prénom Nom ». Utilisées dans les templates et testées.

### La relation 1:N Famille → Paroissien, en résumé

- Une `Famille` a **plusieurs** `Paroissien` (ses `membres`).
- Un `Paroissien` a **au plus une** `Famille` (`famille`, éventuellement `NULL`).
- C'est une relation **1:N** classique, matérialisée par une clé étrangère côté « N »
  (le paroissien), conforme aux **1re et 2e formes normales** (chaque attribut dépend
  de la clé, pas de valeur répétée en liste).

---

## [migrations/0001_initial.py](../apps/paroissiens/migrations/0001_initial.py) — le schéma réellement créé

La migration confirme le schéma SQL : `Famille` puis `Paroissien` avec les deux FK.
On y voit noir sur blanc les `on_delete` :

- `Famille.paroisse` → `on_delete=PROTECT`
- `Paroissien.paroisse` → `on_delete=PROTECT`
- `Paroissien.famille` → `on_delete=SET_NULL`, `blank=True, null=True`

La dépendance `('comptes', '0002_creer_groupes_roles')` montre que cette app se
construit **après** l'app `comptes` (le tenant et les rôles existent déjà).

---

## Le multi-tenant : deux verrous complémentaires

L'isolation par paroisse repose sur **deux mécanismes indépendants** (défense en
profondeur), à connaître pour la soutenance.

### 1. Le manager par défaut — [apps/comptes/managers.py](../apps/comptes/managers.py)

`objects = creer_manager_paroisse()` sur chaque modèle installe un manager dont le
`get_queryset()` filtre automatiquement sur la paroisse courante :

```python
class ParoisseManager(models.Manager.from_queryset(ParoisseQuerySet)):
    def get_queryset(self):
        return super().get_queryset().de_la_paroisse_courante()
```

La paroisse courante est posée par un middleware dans une `ContextVar`. Hors requête
(migrations, shell, **tests qui créent les objets directement**), aucun filtre n'est
appliqué — c'est pourquoi les tests de modèles peuvent créer des paroissiens de
plusieurs paroisses sans problème. Ce manager protège **aussi le Django Admin**, car
`ModelAdmin.get_queryset()` utilise le manager par défaut.

### 2. Le mixin de vue — [apps/comptes/mixins.py](../apps/comptes/mixins.py)

`FiltrageParoisseMixin` refiltre **explicitement** à chaque vue et rattache la
paroisse à tout objet créé :

```python
class FiltrageParoisseMixin(LoginRequiredMixin):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(paroisse=self.request.paroisse)

    def form_valid(self, form):
        form.instance.paroisse = self.request.paroisse
        return super().form_valid(form)
```

Conséquence : demander le détail d'un paroissien d'une **autre** paroisse renvoie
**404** (l'objet est hors du queryset filtré) — c'est ce que vérifie
`test_isolation_multi_tenant_sur_le_detail`.

---

## [forms.py](../apps/paroissiens/forms.py) — les formulaires

Deux `ModelForm`.

### `FamilleForm`

```python
class FamilleForm(forms.ModelForm):
    class Meta:
        model = Famille
        fields = ["nom", "adresse", "telephone"]
```

Le champ `paroisse` est **volontairement absent** du formulaire : il est renseigné
côté serveur par `FiltrageParoisseMixin.form_valid()`. L'utilisateur ne choisit jamais
sa paroisse, ce qui **empêche toute fuite ou usurpation** de tenant via un formulaire
falsifié.

### `ParoissienForm`

```python
class ParoissienForm(forms.ModelForm):
    class Meta:
        model = Paroissien
        fields = ["nom", "prenom", "sexe", "date_naissance", "adresse",
                  "telephone", "email", "photo", "famille"]
        widgets = {"date_naissance": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if paroisse is not None:
            self.fields["famille"].queryset = Famille.objects.filter(paroisse=paroisse)
        self.fields["famille"].required = False
```

Points à défendre :

- **`widget DateInput type="date"`** : affiche un vrai sélecteur de date HTML5.
- **`paroisse` passé en argument** : les vues `Create`/`Update` injectent la paroisse
  courante via `get_form_kwargs()`. Le `__init__` restreint alors la **liste
  déroulante des familles à celles de la paroisse** — on ne peut pas rattacher un
  paroissien à une famille d'une autre paroisse. Isolation multi-tenant jusque dans
  le formulaire.
- **`famille` rendue facultative** (`required = False`) : cohérent avec la FK nullable.

---

## [views.py](../apps/paroissiens/views.py) — le contrôleur (MVT / CRUD)

10 vues génériques (2 entités × 5 opérations CRUD). Toutes empilent les mêmes trois
mixins, dans cet ordre :

```python
RoleRequisMixin, ModuleAutoriseMixin, FiltrageParoisseMixin, <VueGénérique>
```

Deux constantes définissent la politique de rôles :

```python
ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)
```

À noter (pour anticiper une question) : le **Curé** et le **superadmin** ne figurent
pas dans ces listes, mais ils sont **toujours autorisés** — c'est codé en dur dans
`RoleRequisMixin.test_func()`. Le **Trésorier**, lui, n'est dans aucune des deux : il
n'a **aucun accès** aux paroissiens (testé).

### Vues Paroissien

| Vue | Base Django | Rôles | Template |
|---|---|---|---|
| `ParoissienListView` | `ListView` | `ROLES_LECTURE` | `paroissien_liste.html` |
| `ParoissienDetailView` | `DetailView` | `ROLES_LECTURE` | `paroissien_detail.html` |
| `ParoissienCreateView` | `CreateView` | `ROLES_ECRITURE` | `paroissien_form.html` |
| `ParoissienUpdateView` | `UpdateView` | `ROLES_ECRITURE` | `paroissien_form.html` |
| `ParoissienDeleteView` | `DeleteView` | `ROLES_ECRITURE` | `paroissien_confirmer_suppression.html` |

Détails de code marquants :

- **`ParoissienListView.get_queryset()`** ajoute `select_related("famille")` (critère
  14 : **jointure optimisée**). La liste affiche la famille de chaque paroissien ; sans
  `select_related`, ce serait une requête SQL par ligne (problème N+1). Ici, une seule
  jointure SQL.

  ```python
  def get_queryset(self):
      return super().get_queryset().select_related("famille").order_by("nom", "prenom")
  ```

- **`ParoissienCreateView` / `UpdateView`** injectent la paroisse dans le formulaire :

  ```python
  def get_form_kwargs(self):
      kwargs = super().get_form_kwargs()
      kwargs["paroisse"] = self.request.user.paroisse
      return kwargs
  ```

- **`ParoissienCreateView.form_valid()`** applique en plus une **règle de facturation**
  (limite du nombre de paroissiens selon l'offre d'abonnement) avant d'enregistrer :

  ```python
  def form_valid(self, form):
      abonnement = getattr(self.request.paroisse, "abonnement", None)
      if abonnement is not None:
          limite = abonnement.max_paroissiens()
          if limite is not None and Paroissien.objects.filter(
                  paroisse=self.request.paroisse).count() >= limite:
              messages.error(self.request, f"Votre offre ... est limitée à {limite} ...")
              return redirect("paroissiens:paroissien_liste")
      messages.success(self.request, "Paroissien enregistré.")
      return super().form_valid(form)
  ```

  Si la limite est atteinte, on refuse et on redirige avec un message d'erreur ;
  sinon on confirme (« Paroissien enregistré. »).

- **Chaque `form_valid` d'écriture** émet un **message flash** cohérent avec le brief
  (« Paroissien enregistré. », « Modifications enregistrées. », « Paroissien
  supprimé. »).

- **Les vues Delete** ont un `success_url = reverse_lazy(...)` qui renvoie à la liste
  après suppression.

### Vues Famille

Mêmes 5 opérations, mêmes mixins et mêmes rôles. Particularités :

- **`FamilleDetailView.get_queryset()`** ajoute `prefetch_related("membres")` (critère
  14) : le détail affiche la liste des membres de la famille ; `prefetch_related`
  charge tous les membres en **une requête supplémentaire** au lieu d'une par membre.

  ```python
  def get_queryset(self):
      return super().get_queryset().prefetch_related("membres")
  ```

- `FamilleForm` n'a pas besoin de connaître la paroisse (pas de champ dépendant du
  tenant), donc pas de `get_form_kwargs()` surchargé.

---

## [urls.py](../apps/paroissiens/urls.py) — le routage

Namespace `app_name = "paroissiens"`. 10 routes, une par vue, avec des noms explicites
(`paroissien_liste`, `paroissien_creer`, `paroissien_detail`, `paroissien_modifier`,
`paroissien_supprimer`, et les équivalents `famille_*`). Les URLs de famille sont
préfixées par `familles/`. Ces noms sont réutilisés partout via `{% url %}` dans les
templates et `reverse()` dans les vues — aucun chemin en dur.

---

## [admin.py](../apps/paroissiens/admin.py) — backoffice (critère 15)

```python
@admin.register(Famille)
class FamilleAdmin(admin.ModelAdmin):
    list_display = ("nom", "ville_via_adresse", "telephone", "paroisse")
    search_fields = ("nom", "adresse")
    list_filter = ("paroisse",)

    @admin.display(description="adresse")
    def ville_via_adresse(self, obj):
        return obj.adresse or "—"


@admin.register(Paroissien)
class ParoissienAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "sexe", "date_naissance", "famille", "paroisse")
    search_fields = ("nom", "prenom", "email", "telephone")
    list_filter = ("paroisse", "sexe")
    autocomplete_fields = ["famille"]
    list_select_related = ("famille", "paroisse")
```

Points à défendre :

- **`list_display`, `search_fields`, `list_filter`** couvrent le critère 15 (colonnes,
  recherche, filtres) pour les deux entités.
- **`autocomplete_fields = ["famille"]`** : au lieu d'un `<select>` géant listant
  toutes les familles, un champ de recherche asynchrone. C'est aussi ce qui impose
  d'avoir `search_fields` sur `FamilleAdmin` (Django l'exige pour l'autocomplétion).
- **`list_select_related`** : optimise la liste admin (jointure au lieu de N+1),
  cohérent avec le critère 14.
- **`@admin.display`** : une colonne calculée personnalisée (`ville_via_adresse`).
- L'admin hérite du **filtrage multi-tenant** via le manager par défaut du modèle
  (voir §manager) : le `list_filter = ("paroisse",)` reste utile pour le superadmin,
  qui n'est jamais filtré.

---

## [apps.py](../apps/paroissiens/apps.py)

Configuration standard : `default_auto_field = "BigAutoField"` (clés primaires
`BigAutoField`), `name = "apps.paroissiens"`, `label = "paroissiens"`,
`verbose_name = "Paroissiens"`.

---

## Templates — `templates/paroissiens/` (couche Vue du MVT)

Les 8 templates étendent tous `base_app.html` (mise en page commune : navigation
latérale, thème liturgique custom). Ils ne contiennent **aucune logique métier**, juste
de l'affichage — séparation MVT respectée.

| Template | Rôle |
|---|---|
| `paroissien_liste.html` | Tableau `.table-registre` des paroissiens (Nom, Prénom, Sexe, Date de naissance, Famille), liens vers les fiches, **pagination** (`is_paginated`), état vide « Aucun paroissien pour l'instant. Ajoutez le premier. » |
| `paroissien_detail.html` | Fiche d'un paroissien en liste de définitions `<dl>`, lien vers la famille rattachée, boutons Modifier / Supprimer |
| `paroissien_form.html` | Formulaire création/édition ; `enctype="multipart/form-data"` (**obligatoire pour l'upload de photo**) ; titre dynamique selon `object` ; bouton « Enregistrer le paroissien » |
| `paroissien_confirmer_suppression.html` | Page de confirmation avant suppression (POST + CSRF), avertit que l'action est irréversible |
| `famille_liste.html` | Tableau des familles (Nom, Adresse, Téléphone), pagination, état vide |
| `famille_detail.html` | Fiche famille + **tableau des membres** via `famille.membres.all` (illustre la relation 1:N côté « 1 ») |
| `famille_form.html` | Formulaire création/édition famille (pas de `multipart`, aucun fichier) |
| `famille_confirmer_suppression.html` | Confirmation ; précise que « les paroissiens rattachés ne seront pas supprimés, seulement détachés » (reflète `SET_NULL`) |

Détails défendables :

- **Pagination** : les `ListView` ont `paginate_by = 25` ; les templates affichent
  « Page X / N » avec des boutons Précédent/Suivant. Chiffres en classe `.numerique`
  (chiffres tabulaires, conformément à la direction artistique du brief).
- **`get_sexe_display`** utilisé dans les templates : affiche « Masculin »/« Féminin »
  plutôt que « M »/« F ».
- **`enctype="multipart/form-data"`** sur `paroissien_form.html` seulement : c'est ce
  qui permet le transfert du fichier photo. Le template famille ne l'a pas car il n'a
  pas de champ fichier.
- **CSRF** : tous les `<form method="post">` incluent `{% csrf_token %}`.
- **États vides** rédigés comme des invitations à agir, conformément au brief.

---

## Tests

### [tests/test_models.py](../apps/paroissiens/tests/test_models.py) — 3 tests (métier des modèles)

- **`test_creation_famille`** : crée une `Famille` et vérifie qu'elle a une clé primaire
  et que `str(famille) == "Mbala"` (méthode `__str__`).
- **`test_creation_paroissien_rattache_a_une_famille`** : crée un `Paroissien` lié à une
  famille, vérifie le lien `paroissien.famille == famille`, la méthode métier
  `nom_complet() == "Jean Mbala"` et `str(paroissien) == "Jean Mbala"`.
- **`test_suppression_famille_detache_les_paroissiens_sans_les_supprimer`** : LE test
  qui prouve `on_delete=SET_NULL`. On supprime la famille, on recharge le paroissien
  (`refresh_from_db`) et on vérifie que `paroissien.famille is None` — le paroissien
  survit, seul le lien est coupé.

### [tests/test_vues.py](../apps/paroissiens/tests/test_vues.py) — 6 tests (permissions + isolation)

Un helper `creer_utilisateur(paroisse, nom_groupe, username)` crée un utilisateur et
l'ajoute au groupe de rôle voulu.

- **`test_secretaire_peut_creer_un_paroissien`** : un Secrétaire POST le formulaire de
  création → redirection 302, et le paroissien créé porte bien la paroisse de son
  auteur (`paroissien.paroisse == paroisse`) — prouve que `form_valid` rattache
  automatiquement la paroisse.
- **`test_lecteur_ne_peut_pas_creer_un_paroissien`** : un Lecteur qui GET la page de
  création reçoit **403** (interdit en écriture — `ROLES_ECRITURE` ne contient que
  Secrétaire).
- **`test_lecteur_peut_consulter_la_liste`** : un Lecteur peut voir la liste (**200**) —
  droit de lecture.
- **`test_tresorier_n_a_pas_acces_aux_paroissiens`** : un Trésorier reçoit **403** même
  en lecture (il n'est dans aucune des deux listes de rôles).
- **`test_isolation_multi_tenant_sur_la_liste`** : deux paroissiens dans deux paroisses
  différentes ; un Secrétaire de la paroisse A voit « Mbala » (sa paroisse) mais **pas**
  « Kalonji » (l'autre paroisse) dans la liste.
- **`test_isolation_multi_tenant_sur_le_detail`** : accéder au détail d'un paroissien
  d'une **autre** paroisse renvoie **404** (le filtrage le rend invisible).

Ces tests couvrent d'un coup les critères **7** (rôles), **4/§4** (multi-tenant) et
**11** (tests).

---

## Questions probables du jury & réponses

**Q1. Comment garantissez-vous qu'une paroisse ne voie jamais les paroissiens d'une
autre ?**
Deux verrous. D'abord un **manager par défaut** (`creer_manager_paroisse()`) qui filtre
tout queryset sur la paroisse courante, y compris dans l'admin. Ensuite, dans chaque
vue, `FiltrageParoisseMixin.get_queryset()` refiltre explicitement sur
`self.request.paroisse`. C'est une **défense en profondeur**. Le test
`test_isolation_multi_tenant_sur_le_detail` prouve qu'un accès croisé renvoie 404, et
`..._sur_la_liste` qu'un paroissien étranger n'apparaît pas dans la liste.

**Q2. Que se passe-t-il si on supprime une famille qui a des membres ?**
Rien n'est perdu. La FK `famille` a `on_delete=models.SET_NULL` : les paroissiens sont
**détachés** (leur champ `famille` repasse à `NULL`), pas supprimés. C'est un choix
métier — une famille peut se recomposer, mais les personnes restent au registre. C'est
testé par `test_suppression_famille_detache_les_paroissiens_sans_les_supprimer`.

**Q3. Pourquoi `PROTECT` sur `paroisse` mais `SET_NULL` sur `famille` ?**
Ce sont deux sémantiques différentes. La **paroisse** est le tenant : supprimer une
paroisse qui contient encore des données serait une erreur grave, donc `PROTECT` bloque
l'opération (intégrité). La **famille** est un simple regroupement facultatif : sa
suppression ne doit pas détruire les personnes, donc `SET_NULL`.

**Q4. Où est la relation 1:N et comment la voit-on dans l'interface ?**
Côté modèle : la FK `famille` sur `Paroissien` avec `related_name="membres"`. Une
famille a `N` membres, un membre a `0..1` famille. Côté interface : la fiche famille
(`famille_detail.html`) liste `famille.membres.all` dans un tableau ; le détail
paroissien affiche un lien vers sa famille.

**Q5. Comment gérez-vous l'upload de la photo ?**
Le modèle utilise `ImageField(upload_to="paroissiens/")` : les fichiers vont dans
`MEDIA_ROOT/paroissiens/`. Le formulaire inclut le champ `photo`, et le template
`paroissien_form.html` porte `enctype="multipart/form-data"` — indispensable pour
transmettre un fichier. `ImageField` valide en plus que c'est bien une image (via
Pillow).

**Q6. Où sont les règles de rôle et comment le Curé est-il traité ?**
Dans `RoleRequisMixin` (app `comptes`), combiné aux constantes `ROLES_LECTURE` et
`ROLES_ECRITURE` de `views.py`. La lecture est ouverte au Secrétaire et au Lecteur ;
l'écriture au seul Secrétaire. Le **Curé et le superadmin sont toujours autorisés**
(codé en dur dans `test_func()`), conformément au §7 (« Curé : accès complet »). Le
Trésorier n'a aucun accès ici. Quatre tests couvrent ces cas (403 pour Lecteur en
écriture et Trésorier, 200/302 pour Secrétaire et Lecteur en lecture).

**Q7. En quoi respectez-vous le pattern MVT / MVC ?**
Séparation stricte : les **modèles** portent les données et la logique métier
(`nom_complet`, `__str__`) ; les **templates** ne font que de l'affichage (aucune
requête, aucune règle) ; les **vues** (contrôleurs) orchestrent — filtrage, permissions,
formulaires. On utilise les vues génériques Django (`ListView`, `CreateView`…) et des
**mixins** réutilisables, ce qui est de la POO appliquée au contrôleur.

**Q8. Comment évitez-vous le problème des N+1 requêtes ?**
Sur la liste des paroissiens, `select_related("famille")` fait une **jointure SQL**
unique pour ramener la famille de chaque ligne. Sur le détail d'une famille,
`prefetch_related("membres")` charge tous les membres en une requête. Dans l'admin,
`list_select_related` fait de même. C'est le critère 14 (jointures optimisées).

**Q9. Le champ paroisse n'est pas dans le formulaire — n'est-ce pas un oubli ?**
Non, c'est volontaire et c'est une mesure de **sécurité multi-tenant**. Si `paroisse`
était un champ du formulaire, un utilisateur mal intentionné pourrait le falsifier pour
écrire dans une autre paroisse. À la place, `FiltrageParoisseMixin.form_valid()` force
`form.instance.paroisse = self.request.paroisse` côté serveur. Le test
`test_secretaire_peut_creer_un_paroissien` vérifie que la bonne paroisse est bien
assignée.

**Q10. Que fait la limite de paroissiens dans `ParoissienCreateView.form_valid` ?**
C'est une **règle de facturation** liée à l'offre d'abonnement de la paroisse. Avant
d'enregistrer, on lit `abonnement.max_paroissiens()` ; si la limite est atteinte, on
refuse la création et on affiche un message invitant à changer d'offre. Si la paroisse
n'a pas d'abonnement (cas de test, comptes internes), aucune limite ne s'applique — la
facturation ne doit pas bloquer un usage interne de confiance.
