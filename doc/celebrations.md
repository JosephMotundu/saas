# App `celebrations` — célébrations et intentions de messe

Fiche de révision pour la soutenance. Objectif : pouvoir défendre chaque ligne
de code de l'app devant le jury.

## Rôle de l'app

L'app `celebrations` gère deux choses complémentaires dans la vie d'une paroisse :

1. **Les célébrations** (`Celebration`) : les messes, vigiles et fêtes
   planifiées — une date, une heure, un type, un célébrant, un lieu.
2. **Les intentions de messe** (`IntentionMesse`) : les demandes des paroissiens
   (« une messe pour le repos de l'âme de X », « en action de grâce ») rattachées
   à une célébration précise, avec un **montant d'offrande** et sa **devise**.

Le point métier important à retenir : **les offrandes d'intentions de messe ne
restent pas dans leur coin — elles alimentent le solde comptable de la paroisse**
(voir la section [Lien avec les finances](#lien-avec-les-finances-le-cœur-métier)).
C'est le fil rouge à connaître pour la soutenance.

Fichiers de l'app :

- [models.py](../apps/celebrations/models.py) — les deux modèles.
- [forms.py](../apps/celebrations/forms.py) — les formulaires.
- [views.py](../apps/celebrations/views.py) — les vues (contrôleurs MVT).
- [admin.py](../apps/celebrations/admin.py) — le backoffice.
- [urls.py](../apps/celebrations/urls.py) — le routage.
- [apps.py](../apps/celebrations/apps.py) — la config de l'app.
- [templates/celebrations/](../apps/celebrations/templates/celebrations/) — les 6 gabarits.
- [tests/](../apps/celebrations/tests/) — tests modèles + tests vues.
- Modules partagés utilisés : [core/devises.py](../apps/core/devises.py),
  [comptes/managers.py](../apps/comptes/managers.py),
  [comptes/mixins.py](../apps/comptes/mixins.py),
  [finances/services.py](../apps/finances/services.py).

---

## Critères du jury démontrés ici

| Critère (§3 du brief) | Où le montrer dans cette app |
|---|---|
| **1 — BDD relationnelle, relation 1:N** | `Celebration` 1:N `IntentionMesse` via `ForeignKey(Celebration, related_name="intentions")` dans [models.py](../apps/celebrations/models.py). Contraintes d'intégrité : `on_delete=PROTECT`, `null=True/blank=True` sur `montant_offrande`, `default` sur `devise` et `statut`. |
| **6 — Architecture MVT** | Séparation stricte : Model ([models.py](../apps/celebrations/models.py)), Vue = Template ([templates/](../apps/celebrations/templates/celebrations/)), Contrôleur = View ([views.py](../apps/celebrations/views.py)). Aucune logique métier dans les templates. |
| **CRUD complet (critère 1)** | Create / Read (liste + détail) / Update pour les deux modèles via les vues génériques Django, routées dans [urls.py](../apps/celebrations/urls.py). |
| **7 — Rôles et permissions** | `RoleRequisMixin` avec `roles_autorises` : lecture pour Secrétaire + Lecteur, écriture réservée au Secrétaire (le Curé passe partout). |
| **9 — POO / méthodes métier** | Méthode `offrande_affichee()` sur le modèle `IntentionMesse`, `__str__`, `get_absolute_url`. Logique de solde déportée dans une couche `services/` ([finances/services.py](../apps/finances/services.py)). |
| **4 — Multi-tenant / isolation** | Manager `creer_manager_paroisse()` + `FiltrageParoisseMixin` : double filtrage par paroisse. Testé. |
| **11 — Tests** | [test_models.py](../apps/celebrations/tests/test_models.py) et [test_vues.py](../apps/celebrations/tests/test_vues.py) : modèles, permissions, isolation. |
| **14 — Jointures optimisées** | `select_related("celebration")` sur la liste des intentions, `prefetch_related("intentions")` sur le détail d'une célébration. |
| **15 — Backoffice admin** | [admin.py](../apps/celebrations/admin.py) : `list_display`, `list_filter`, `search_fields`, inline. |

---

## Fichier par fichier

### [models.py](../apps/celebrations/models.py) — les deux entités

C'est le cœur de l'app. Deux modèles.

#### Le modèle `Celebration`

```python
class Celebration(models.Model):
    TYPE_CHOICES = [
        ("messe", "Messe"),
        ("vigile", "Vigile"),
        ("fete", "Fête"),
        ("autre", "Autre"),
    ]

    date = models.DateField("date")
    heure = models.TimeField("heure")
    type_celebration = models.CharField("type", max_length=20, choices=TYPE_CHOICES)
    celebrant = models.CharField("célébrant", max_length=200)
    lieu = models.CharField("lieu", max_length=200, blank=True)
    paroisse = models.ForeignKey(
        Paroisse, verbose_name="paroisse", related_name="celebrations", on_delete=models.PROTECT
    )

    objects = creer_manager_paroisse()
```

Points à défendre :

- **`type_celebration` est un champ à choix contraints** (`TYPE_CHOICES`) : la
  base ne peut contenir qu'une des quatre valeurs. Le libellé lisible s'obtient
  par `get_type_celebration_display()` (méthode générée par Django), utilisée
  dans les templates.
- **`lieu` est `blank=True`** : optionnel dans les formulaires (le lieu par
  défaut est l'église de la paroisse).
- **`paroisse` = FK vers le tenant.** `on_delete=PROTECT` : on interdit de
  supprimer une paroisse tant qu'il lui reste des célébrations — garde-fou
  d'intégrité, on ne perd jamais un registre par accident.
- **`related_name="celebrations"`** : depuis une paroisse on écrit
  `paroisse.celebrations.all()`.
- **`objects = creer_manager_paroisse()`** : le manager par défaut filtre
  automatiquement sur la paroisse courante (isolation multi-tenant, §4). Voir
  [managers.py](../apps/comptes/managers.py).

Méthodes (POO, critère 9) :

```python
def __str__(self):
    return f"{self.get_type_celebration_display()} du {self.date} à {self.heure}"

def get_absolute_url(self):
    return reverse("celebrations:celebration_detail", args=[self.pk])
```

`Meta.ordering = ["date", "heure"]` : les célébrations sortent toujours dans
l'ordre chronologique.

#### Le modèle `IntentionMesse`

```python
class IntentionMesse(models.Model):
    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("celebree", "Célébrée"),
        ("annulee", "Annulée"),
    ]

    demandeur = models.CharField("demandeur", max_length=200)
    intention = models.CharField("intention", max_length=300)
    montant_offrande = models.DecimalField(
        "montant de l'offrande", max_digits=12, decimal_places=2, null=True, blank=True
    )
    devise = models.CharField(
        "devise", max_length=3, choices=DEVISE_CHOICES, default="CDF"
    )
    statut = models.CharField(
        "statut", max_length=20, choices=STATUT_CHOICES, default="en_attente"
    )
    celebration = models.ForeignKey(
        Celebration,
        verbose_name="célébration",
        related_name="intentions",
        on_delete=models.PROTECT,
    )
    paroisse = models.ForeignKey(Paroisse, verbose_name="paroisse", on_delete=models.PROTECT)

    objects = creer_manager_paroisse()
```

Points à défendre :

- **`montant_offrande` est un `DecimalField`, pas un `Float`.** C'est le bon
  choix pour de l'argent : pas d'erreur d'arrondi binaire. `max_digits=12,
  decimal_places=2`. Il est `null=True, blank=True` : **une intention peut
  exister sans offrande** (un paroissien peut demander une messe sans donner
  d'argent). Ce détail est important pour comprendre le calcul du solde côté
  finances (on exclut les montants nuls, voir plus bas).
- **`devise`** : champ récemment ajouté (migration `0002`, voir plus bas), à
  choix (`DEVISE_CHOICES` importé de [core/devises.py](../apps/core/devises.py)),
  `default="CDF"` (franc congolais). C'est ce qui permet d'enregistrer une
  offrande en francs **ou** en dollars.
- **`statut`** : cycle de vie de l'intention (`en_attente` → `celebree` /
  `annulee`), `default="en_attente"`.
- **`celebration` = FK vers `Celebration`**, `related_name="intentions"`. C'est
  le côté « N » de la relation 1:N. `on_delete=PROTECT` : impossible de
  supprimer une célébration qui porte des intentions.
- **`paroisse`** dupliquée sur l'intention (pas seulement via la célébration) :
  choix assumé pour que le manager multi-tenant filtre l'intention directement,
  sans jointure, et pour que l'agrégation du solde côté finances reste simple.

Méthode métier centrale (critère 9, POO) :

```python
def offrande_affichee(self):
    """Montant de l'offrande avec sa devise, ou « — » si non renseigné."""
    if self.montant_offrande is None:
        return "—"
    return formater_montant(self.montant_offrande, self.devise)
```

À défendre : la **logique de présentation d'un montant vit sur le modèle**, pas
dans le template. Le template appelle juste `{{ intention.offrande_affichee }}`.
Résultat typique : `« 10 FC »` ou `« 25 $ »`, ou `« — »` si pas d'offrande. La
mise en forme du symbole est déléguée à `formater_montant()` du module partagé
`core.devises` — un seul endroit pour tout le projet.

`Meta.ordering = ["-celebration__date"]` : les intentions sortent les plus
récentes d'abord, en s'appuyant sur la date de la célébration liée (tri par
jointure).

#### La relation 1:N Celebration → IntentionMesse

C'est LE point relationnel de l'app (critère 1).

- **Un** `Celebration` peut porter **plusieurs** `IntentionMesse`.
- **Une** `IntentionMesse` appartient à **exactement une** `Celebration`
  (la FK n'est pas `null=True` : intention orpheline impossible).
- Navigation : `celebration.intentions.all()` (sens 1→N) et
  `intention.celebration` (sens N→1).

Le test `test_creation_intention_rattachee_a_une_celebration` vérifie
explicitement `intention in celebration.intentions.all()`.

---

### [core/devises.py](../apps/core/devises.py) — le module partagé des devises

Pas dans l'app `celebrations`, mais indispensable pour la comprendre. Il est
placé dans `core` (une app « feuille », sans dépendance métier) exprès :

```python
DEVISE_CHOICES = [
    ("CDF", "Franc congolais (FC)"),
    ("USD", "Dollar (USD)"),
]

SYMBOLES_DEVISE = {"CDF": "FC", "USD": "$"}

def formater_montant(montant, devise):
    """Rend un montant avec le symbole de sa devise, ex. « 45 FC », « 120 $ »."""
    return f"{montant} {SYMBOLES_DEVISE.get(devise, devise)}"
```

Argument à défendre : **`celebrations` et `finances` partagent la même
définition de devise sans dépendre l'une de l'autre.** Le commentaire en tête du
fichier le dit : le module est neutre pour éviter une dépendance croisée entre
les deux apps métier. La **décision produit** y est aussi documentée : *dollars
et francs ne sont jamais additionnés entre eux ; chaque montant porte sa devise
et le solde est calculé par devise.* C'est ce qui justifie que le champ `devise`
existe sur chaque intention.

---

### [views.py](../apps/celebrations/views.py) — les contrôleurs (MVT)

Huit vues, toutes des **vues génériques** Django (`ListView`, `DetailView`,
`CreateView`, `UpdateView`) : c'est la partie « V = View = contrôleur » du
pattern MVT.

Deux constantes définissent la politique de rôles en haut du fichier :

```python
ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)
```

Chaque vue combine **trois mixins** dans un ordre précis :

- `RoleRequisMixin` — vérifie le rôle (permissions, §7).
- `FiltrageParoisseMixin` — isole les données par paroisse (§4).
- une vue générique Django — le CRUD.

Exemples clés :

```python
class CelebrationListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    model = Celebration
    template_name = "celebrations/celebration_liste.html"
    context_object_name = "celebrations"
    paginate_by = 25
    roles_autorises = ROLES_LECTURE
```

- `paginate_by = 25` : pagination (utilisée dans les templates via
  `is_paginated` / `page_obj`).
- `roles_autorises = ROLES_LECTURE` : Secrétaire **et** Lecteur peuvent
  consulter.

```python
class CelebrationDetailView(RoleRequisMixin, FiltrageParoisseMixin, DetailView):
    ...
    def get_queryset(self):
        return super().get_queryset().prefetch_related("intentions")
```

- **`prefetch_related("intentions")`** (critère 14) : le détail d'une célébration
  affiche toutes ses intentions ; on précharge la relation 1:N en **une seule
  requête supplémentaire** au lieu d'une par intention (anti N+1).

```python
class IntentionMesseListView(RoleRequisMixin, FiltrageParoisseMixin, ListView):
    ...
    def get_queryset(self):
        return super().get_queryset().select_related("celebration")
```

- **`select_related("celebration")`** (critère 14) : la liste des intentions
  affiche la date de chaque célébration ; on fait une **jointure SQL** pour
  éviter une requête par ligne.

Les vues de création/modification d'intention injectent la paroisse courante
dans le formulaire :

```python
class IntentionMesseCreateView(...):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["paroisse"] = self.request.user.paroisse
        return kwargs
```

But : que la liste déroulante des célébrations du formulaire ne montre que les
célébrations de **cette** paroisse (voir forms.py). Toutes les vues d'écriture
posent aussi un message de confirmation (`messages.success(...)`), en respectant
le ton du brief (« Célébration enregistrée. »).

Note MVT importante : **aucune vue ne calcule le solde financier.** Ce calcul
vit dans la couche `services` de l'app finances. Séparation des responsabilités.

---

### [forms.py](../apps/celebrations/forms.py) — les formulaires

Deux `ModelForm`.

```python
class CelebrationForm(forms.ModelForm):
    class Meta:
        model = Celebration
        fields = ["date", "heure", "type_celebration", "celebrant", "lieu"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "heure": forms.TimeInput(attrs={"type": "time"}),
        }
```

- Le champ `paroisse` n'est **pas** dans `fields` : il ne doit jamais être choisi
  par l'utilisateur, il est posé automatiquement par `FiltrageParoisseMixin`
  (`form.instance.paroisse = self.request.paroisse`). Anti-fuite de tenant.
- `widgets` : force les sélecteurs natifs de date et d'heure du navigateur
  (`type="date"` / `type="time"`), meilleure ergonomie mobile.

```python
class IntentionMesseForm(forms.ModelForm):
    class Meta:
        model = IntentionMesse
        fields = ["celebration", "demandeur", "intention", "montant_offrande", "devise", "statut"]

    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if paroisse is not None:
            self.fields["celebration"].queryset = Celebration.objects.filter(paroisse=paroisse)
```

À défendre : le `__init__` reçoit la `paroisse` (injectée par la vue) et
**restreint la liste déroulante des célébrations à celles de la paroisse**. Sans
ça, un utilisateur pourrait techniquement rattacher son intention à une
célébration d'une autre paroisse. C'est une **isolation multi-tenant au niveau
du formulaire**, en plus du manager et du mixin. `devise` figure bien dans
`fields` : l'utilisateur choisit francs ou dollars à la saisie.

---

### [urls.py](../apps/celebrations/urls.py) — le routage

`app_name = "celebrations"` (namespace). Huit routes, deux familles :

| URL | Vue | Nom |
|---|---|---|
| `""` | `CelebrationListView` | `celebration_liste` |
| `"nouvelle/"` | `CelebrationCreateView` | `celebration_creer` |
| `"<int:pk>/"` | `CelebrationDetailView` | `celebration_detail` |
| `"<int:pk>/modifier/"` | `CelebrationUpdateView` | `celebration_modifier` |
| `"intentions/"` | `IntentionMesseListView` | `intention_liste` |
| `"intentions/nouvelle/"` | `IntentionMesseCreateView` | `intention_creer` |
| `"intentions/<int:pk>/"` | `IntentionMesseDetailView` | `intention_detail` |
| `"intentions/<int:pk>/modifier/"` | `IntentionMesseUpdateView` | `intention_modifier` |

CRUD complet (Create / Read liste + détail / Update). Pas de route de
suppression : cohérent avec `on_delete=PROTECT` — un registre de célébrations ne
se supprime pas à la légère.

---

### [admin.py](../apps/celebrations/admin.py) — le backoffice (critère 15)

```python
class IntentionMesseInline(admin.TabularInline):
    model = IntentionMesse
    extra = 0
    fields = ("demandeur", "intention", "montant_offrande", "devise", "statut")

@admin.register(Celebration)
class CelebrationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type_celebration", "date", "heure", "celebrant", "paroisse")
    list_filter = ("paroisse", "type_celebration", "date")
    search_fields = ("celebrant", "lieu")
    inlines = [IntentionMesseInline]

@admin.register(IntentionMesse)
class IntentionMesseAdmin(admin.ModelAdmin):
    list_display = ("demandeur", "intention", "statut", "montant_offrande", "devise", "celebration", "paroisse")
    list_filter = ("paroisse", "statut", "devise")
    search_fields = ("demandeur", "intention")
    list_select_related = ("celebration", "paroisse")
```

À défendre :

- **`IntentionMesseInline`** : depuis la fiche d'une célébration dans l'admin, on
  saisit directement ses intentions — reflet visuel de la relation 1:N.
- `list_display` / `list_filter` / `search_fields` : exigés par le critère 15.
  On peut filtrer les intentions par `devise` et par `statut`.
- `list_select_related = ("celebration", "paroisse")` : optimisation des
  jointures aussi dans l'admin (critère 14).
- L'isolation par paroisse dans l'admin est portée par le manager par défaut du
  modèle (`ModelAdmin.get_queryset()` l'utilise) — voir le commentaire de
  [managers.py](../apps/comptes/managers.py).

---

### [apps.py](../apps/celebrations/apps.py) — configuration

```python
class CelebrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.celebrations"
    label = "celebrations"
    verbose_name = "Célébrations"
```

Rien de spécial : `label = "celebrations"` fixe le libellé court de l'app,
`verbose_name` son nom affiché dans l'admin.

---

### [templates/celebrations/](../apps/celebrations/templates/celebrations/) — les vues (V du MVT)

Six gabarits, tous héritant de `base_app.html`. Aucune logique métier dedans :
ils se contentent d'afficher les données préparées par les vues.

| Template | Rôle |
|---|---|
| `celebration_liste.html` | Tableau des célébrations (`table-registre`), pagination, bouton « Ajouter une célébration », lien vers les intentions. État vide : « Aucune célébration planifiée pour l'instant. Ajoutez la première. » |
| `celebration_detail.html` | Fiche d'une célébration + **son tableau d'intentions** (`celebration.intentions.all`), affichant `intention.offrande_affichee`. Boutons Modifier / Ajouter une intention. |
| `celebration_form.html` | Formulaire d'ajout/modification (partagé création + édition via `{% if object %}`). Champs rendus par le partial `partials/_form_field.html`. |
| `intention_liste.html` | Tableau des intentions : demandeur, intention, date de célébration, `offrande_affichee`, statut. Pagination. |
| `intention_detail.html` | Fiche d'une intention avec lien vers sa célébration, offrande affichée avec sa devise, statut. |
| `intention_form.html` | Formulaire d'ajout/modification d'intention. |

À noter : la colonne « Offrande » des tableaux appelle `{{ intention.offrande_affichee }}`
— la méthode métier du modèle, pas un calcul dans le template. Le statut est
affiché via `{{ intention.get_statut_display }}` dans une étiquette. Les montants
portent la classe CSS `numerique` (chiffres tabulaires, exigence de la direction
artistique du brief).

---

## Lien avec les finances (le cœur métier)

C'est LA question que le jury posera. Réponse ancrée dans
[finances/services.py](../apps/finances/services.py).

Le solde d'une paroisse n'est **pas** stocké : il est **recalculé** par la
fonction `calculer_situation_financiere(paroisse)`. Les recettes viennent de
**trois** sources — les dons, les offrandes de quête (`OffrandeMesse`), et **les
offrandes des intentions de messe**. Extrait :

```python
offrandes_intentions = _totaux_par_devise(
    IntentionMesse.objects.filter(paroisse=paroisse)
    .exclude(statut="annulee")
    .exclude(montant_offrande__isnull=True),
    champ_montant="montant_offrande",
)
```

Ce qu'il faut savoir défendre :

1. **Les offrandes d'intentions rejoignent la comptabilité par agrégation en
   base**, pas par recopie. `finances.services` importe directement
   `IntentionMesse` depuis l'app `celebrations` et fait un `Sum` groupé par
   `devise` (`_totaux_par_devise`). Pas de duplication de donnée, pas de risque
   de désynchronisation.
2. **On exclut les intentions annulées** (`.exclude(statut="annulee")`) : une
   messe annulée ne compte pas dans les recettes. C'est là que le champ `statut`
   prend son sens comptable.
3. **On exclut les offrandes nulles** (`.exclude(montant_offrande__isnull=True)`) :
   cohérent avec le fait que `montant_offrande` soit `null=True` — une intention
   sans argent n'ajoute rien au solde.
4. **Le solde est calculé par devise, jamais mélangé.** La fonction boucle sur
   `DEVISE_CHOICES` et additionne dons + offrandes de messe + offrandes
   d'intentions **dans la même devise** :

```python
for code, _ in DEVISE_CHOICES:
    recettes_devise = (
        dons.get(code, Decimal("0"))
        + offrandes_messe.get(code, Decimal("0"))
        + offrandes_intentions.get(code, Decimal("0"))
    )
    depenses_devise = depenses.get(code, Decimal("0"))
    ...
    "solde": recettes_devise - depenses_devise,
```

C'est la raison d'être du champ `devise` sur `IntentionMesse` : sans lui,
impossible de savoir si une offrande de 20 est en francs ou en dollars, et le
solde serait faux.

En résumé pour la soutenance : **une intention de messe est à la fois un acte
liturgique (registre) et un mouvement de recette (comptabilité), et le champ
`devise` fait le pont entre les deux.**

---

## La migration `devise` (traçabilité)

Le champ `devise` a été ajouté après coup, ce qui se voit dans l'historique des
migrations — bon point pour le critère 10 (historique Git propre) et pour
montrer qu'on maîtrise les migrations Django.

- [0001_initial.py](../apps/celebrations/migrations/0001_initial.py) : crée
  `Celebration` et `IntentionMesse`. À l'origine `montant_offrande` avait
  `max_digits=10` et il n'y avait **pas** de champ `devise`.
- [0002_intentionmesse_devise_and_more.py](../apps/celebrations/migrations/0002_intentionmesse_devise_and_more.py) :
  ajoute `devise` (`default="CDF"`) et fait passer `montant_offrande` à
  `max_digits=12`.

```python
migrations.AddField(
    model_name='intentionmesse',
    name='devise',
    field=models.CharField(choices=[('CDF', 'Franc congolais (FC)'), ('USD', 'Dollar (USD)')], default='CDF', max_length=3, verbose_name='devise'),
),
```

Le `default='CDF'` garantit que les intentions déjà en base au moment de la
migration reçoivent une devise valide (franc congolais) sans intervention
manuelle.

---

## Tests

Deux fichiers, exécutés par pytest-django (`pytestmark = pytest.mark.django_db`).

### [tests/test_models.py](../apps/celebrations/tests/test_models.py)

- **`test_creation_celebration`** : crée une `Celebration`, vérifie qu'elle a
  bien un `pk` et que son `__str__` contient « Messe » (donc que
  `get_type_celebration_display()` marche).
- **`test_creation_intention_rattachee_a_une_celebration`** : crée une intention
  rattachée à une célébration et vérifie **trois choses** :
  - `intention.celebration == celebration` (le sens N→1),
  - `intention.statut == "en_attente"` (la valeur par défaut s'applique),
  - `intention in celebration.intentions.all()` (le sens 1→N, donc la relation
    fonctionne dans les deux sens).

### [tests/test_vues.py](../apps/celebrations/tests/test_vues.py)

Utilise le `client` de test et une fabrique `creer_utilisateur(paroisse,
nom_groupe, username)` qui crée un utilisateur et l'ajoute à un groupe (rôle).

- **`test_secretaire_peut_creer_une_celebration`** : un Secrétaire POST le
  formulaire de création → réponse 302 (redirection = succès) et la célébration
  existe en base. Vérifie CRUD + permission d'écriture.
- **`test_secretaire_peut_creer_une_intention`** : un Secrétaire crée une
  intention (avec `devise: "CDF"`) rattachée à une célébration → 302 et
  `celebration.intentions.count() == 1`. Vérifie la relation 1:N via une vraie
  requête HTTP.
- **`test_lecteur_ne_peut_pas_creer_de_celebration`** : un Lecteur qui GET la
  vue de création reçoit **403 Interdit**. Vérifie que `RoleRequisMixin` bloque
  bien le rôle Lecteur en écriture (§7).
- **`test_isolation_multi_tenant_sur_les_celebrations`** : crée une célébration
  dans une **autre** paroisse (célébrant « Abbé Lumumba »), connecte un
  Secrétaire de Saint Raphaël, et vérifie que « Lumumba » **n'apparaît pas** dans
  la liste. Preuve directe de l'isolation multi-tenant (§4).

---

## Questions probables du jury & réponses

**1. Comment les offrandes de messe rejoignent-elles la comptabilité ?**
Elles ne sont pas recopiées. `finances.services.calculer_situation_financiere()`
importe le modèle `IntentionMesse` et **agrège** les `montant_offrande` par
devise avec un `Sum` SQL, en excluant les intentions annulées et sans montant.
Le solde est donc toujours exact et à jour, sans doublon de donnée.

**2. Pourquoi un champ `devise` sur chaque intention plutôt qu'une devise
globale ?**
Décision produit documentée dans [core/devises.py](../apps/core/devises.py) :
francs congolais et dollars ne s'additionnent jamais. Une paroisse reçoit des
offrandes dans les deux monnaies ; chaque montant doit donc porter sa devise
pour qu'on calcule **un solde par devise**, sans conversion arbitraire.

**3. Qu'est-ce que la méthode `offrande_affichee()` et pourquoi est-elle sur le
modèle ?**
Elle rend le montant avec son symbole (« 10 FC », « 25 $ ») ou « — » si pas
d'offrande. Elle est sur le modèle (POO, critère 9) pour que toute la mise en
forme d'un montant vive à un seul endroit ; les templates l'appellent
directement, sans logique. Elle délègue le symbole à `formater_montant()` du
module partagé.

**4. Expliquez la relation 1:N ici.**
Une célébration porte plusieurs intentions ; chaque intention appartient à une
seule célébration, via `ForeignKey(Celebration, related_name="intentions")`. On
navigue dans les deux sens : `celebration.intentions.all()` et
`intention.celebration`. La FK n'est pas nullable : pas d'intention orpheline.

**5. Pourquoi `on_delete=PROTECT` partout et pas `CASCADE` ?**
Ce sont des registres canoniques et des mouvements financiers : on refuse toute
suppression en chaîne accidentelle. Supprimer une paroisse ou une célébration qui
porte encore des intentions lève une erreur au lieu d'effacer silencieusement
des données comptables. D'ailleurs il n'y a volontairement aucune vue de
suppression.

**6. Comment garantissez-vous qu'une paroisse ne voit pas les célébrations d'une
autre ?**
Triple défense : (a) le manager par défaut `creer_manager_paroisse()` filtre
automatiquement sur la paroisse courante ; (b) `FiltrageParoisseMixin` refiltre
explicitement dans chaque vue ; (c) le formulaire d'intention restreint la liste
des célébrations à la paroisse. Le test
`test_isolation_multi_tenant_sur_les_celebrations` le prouve.

**7. Où sont les optimisations de requêtes (critère 14) ?**
`IntentionMesseListView` fait `select_related("celebration")` (jointure, évite le
N+1 sur la date de célébration) ; `CelebrationDetailView` fait
`prefetch_related("intentions")` (précharge la collection d'intentions). L'admin
utilise aussi `list_select_related`.

**8. Comment un Lecteur est-il empêché de créer une célébration ?**
Les vues d'écriture ont `roles_autorises = ROLES_ECRITURE = ("Secrétaire",)`, et
`RoleRequisMixin.test_func()` renvoie `False` pour un Lecteur → HTTP 403. Le Curé
et le superadmin passent toujours (règle du §7). Testé par
`test_lecteur_ne_peut_pas_creer_de_celebration`.

**9. Une intention peut-elle exister sans offrande ? Que devient-elle dans le
solde ?**
Oui : `montant_offrande` est `null=True, blank=True`. Dans le calcul du solde,
`.exclude(montant_offrande__isnull=True)` l'écarte : elle ne rapporte rien mais
reste un acte liturgique enregistré. `offrande_affichee()` affiche « — ».

**10. Pourquoi le module `devises` est-il dans `core` et pas dans `finances` ou
`celebrations` ?**
Pour éviter une dépendance croisée. `finances` et `celebrations` ont toutes deux
besoin des devises ; si le module vivait dans l'une, l'autre en dépendrait.
Placé dans `core` (app feuille, sans dépendance métier), il est importable par
les deux sans créer de cycle. C'est un argument d'architecture propre.

**11. Le calcul du solde n'est-il pas dans les vues de `celebrations` ? (piège
MVT)**
Non, et c'est volontaire : les vues de `celebrations` ne font que du CRUD. Le
calcul financier vit dans la couche `services` de l'app `finances` (critère 9,
séparation des couches). L'app `celebrations` expose la donnée (`IntentionMesse`)
et l'app `finances` la consomme.
