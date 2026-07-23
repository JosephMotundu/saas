# App `sacrements` — les registres canoniques

> Fiche de révision pour la soutenance. Objectif : pouvoir **défendre** chaque
> ligne de code de cette app devant le jury. Tout ce qui suit est tiré du code
> réel du dépôt ; les liens pointent vers les fichiers sources.

## Rôle de l'app

L'app `sacrements` tient les **registres sacramentels** de la paroisse : baptêmes,
communions, confirmations, mariages, funérailles. Elle reproduit informatiquement
les gros registres reliés d'un secrétariat paroissial : chaque acte reçoit un
**numéro de registre** séquentiel, jamais réutilisé, et l'acte de baptême peut être
enrichi toute la vie durant par des **mentions marginales** (mariage, ordination,
décès), exactement comme le prévoit le droit canonique.

Fichiers de l'app :

- [models.py](../apps/sacrements/models.py) — modèles et logique métier (numérotation, mentions)
- [forms.py](../apps/sacrements/forms.py) — formulaires de saisie, filtrés par paroisse
- [views.py](../apps/sacrements/views.py) — vues CRUD + certificats
- [admin.py](../apps/sacrements/admin.py) — backoffice Django
- [urls.py](../apps/sacrements/urls.py) — routes
- [apps.py](../apps/sacrements/apps.py) — configuration de l'app
- [migrations/0001_initial.py](../apps/sacrements/migrations/0001_initial.py) — schéma BDD
- [tests/test_models.py](../apps/sacrements/tests/test_models.py), [tests/test_vues.py](../apps/sacrements/tests/test_vues.py)
- `templates/sacrements/` — 9 gabarits (voir plus bas)

---

## Critères du jury démontrés ici

| Critère | Où le montrer |
|---|---|
| **1. BDD relationnelle** (relations 1:N, FK, contraintes) | FK `paroissien`, `conjoint1/2`, `paroisse`, `bapteme` ; `UniqueConstraint(paroisse, numero_acte)` ; `NOT NULL` par défaut. Voir [models.py](../apps/sacrements/models.py) et la [migration](../apps/sacrements/migrations/0001_initial.py). |
| **1. CRUD complet** | `ListView / DetailView / CreateView / UpdateView` pour chaque registre. Voir [views.py](../apps/sacrements/views.py). |
| **6. Architecture MVT** | Model (`models.py`) / Template (`templates/`) / View = contrôleur (`views.py`). Séparation stricte : aucune logique SQL dans les templates, aucune présentation dans les modèles. |
| **7. Rôles et permissions** | `RoleRequisMixin` + constantes `ROLES_LECTURE` / `ROLES_ECRITURE` sur chaque vue. Test : le Trésorier reçoit un 403. |
| **9. POO** | Hiérarchie de modèles abstraits `ActeBase → ActePersonnel → Bapteme…` ; méthode métier `generer_numero_acte()` ; mixins de vues factorisés. |
| **Certificats imprimables** | Vues `*CertificatView` + gabarits `acte_certificat.html` / `mariage_certificat.html` (bouton `window.print()` → PDF). |
| **14. Jointures optimisées** | `select_related("paroissien")`, `prefetch_related("mentions_marginales")` dans les querysets. |
| **11. Tests** | `test_models.py` (numérotation, relations, mentions) + `test_vues.py` (permissions, certificat, isolation multi-tenant). |
| **15. Backoffice** | `admin.py` : `list_display`, `list_filter`, `search_fields`, inline des mentions. |
| **Multi-tenant (§4)** | Manager `creer_manager_paroisse()` + FK `paroisse` sur chaque acte + `FiltrageParoisseMixin`. |

---

## `models.py` — le cœur métier

Chemin : [apps/sacrements/models.py](../apps/sacrements/models.py)

### La hiérarchie de classes (POO, critère 9)

Trois niveaux d'héritage, dont deux **abstraits** (pas de table en base) :

```
ActeBase (abstract)         ← champs communs + numérotation
   └── ActePersonnel (abstract)   ← ajoute la FK paroissien
          ├── Bapteme      (PREFIXE = "BAP")  + parrain, marraine
          ├── Communion    (PREFIXE = "COM")
          ├── Confirmation (PREFIXE = "CONF")
          └── Funerailles  (PREFIXE = "FUN")
   └── Mariage (concret, PREFIXE = "MAR")     ← 2 FK conjoints, pas de « paroissien » unique
```

C'est l'argument POO à défendre : au lieu de recopier date/lieu/célébrant/numéro
dans cinq modèles, on **factorise** dans une classe mère abstraite. Le mariage relie
deux paroissiens, il hérite donc directement d'`ActeBase` (et non d'`ActePersonnel`).

### `ActeBase` — champs communs et numérotation

```python
class ActeBase(models.Model):
    PREFIXE = "ACT"
    numero_acte = models.CharField("numéro d'acte", max_length=30, editable=False, blank=True)
    date = models.DateField("date")
    lieu = models.CharField("lieu", max_length=200, blank=True)
    celebrant = models.CharField("célébrant", max_length=200)
    paroisse = models.ForeignKey(Paroisse, on_delete=models.PROTECT)
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    objects = creer_manager_paroisse()

    class Meta:
        abstract = True
        ordering = ["-date"]
```

Points défendables :

- **`abstract = True`** : aucune table `actebase`, seuls les modèles concrets créent des tables.
- **`numero_acte` `editable=False`** : impossible à modifier à la main, il est calculé.
- **`on_delete=models.PROTECT`** sur `paroisse` : on **interdit** de supprimer une paroisse
  qui possède encore des actes. Un registre ne s'efface pas par accident (intégrité référentielle).
- **`date_enregistrement = auto_now_add`** : horodatage automatique, non modifiable (traçabilité).
- **`objects = creer_manager_paroisse()`** : le manager multi-tenant (§4). Tout `Bapteme.objects.all()`
  ne renvoie que les actes de la paroisse courante.

### Méthode métier : `generer_numero_acte()`

```python
def generer_numero_acte(self):
    annee = self.date.year if self.date else timezone.now().year
    compte = (
        type(self)
        .objects.filter(paroisse=self.paroisse, date__year=annee)
        .exclude(pk=self.pk)
        .count()
        + 1
    )
    return f"{self.PREFIXE}-{annee}-{compte:04d}"

def save(self, *args, **kwargs):
    if not self.numero_acte:
        self.numero_acte = self.generer_numero_acte()
    super().save(*args, **kwargs)
```

À bien comprendre et savoir expliquer :

- **Format** : `BAP-2026-0001` = préfixe du sacrement + année + compteur sur 4 chiffres.
- **`type(self)`** : renvoie la classe concrète réelle (`Bapteme`, `Communion`…). Grâce à ça,
  la même méthode écrite une seule fois dans la classe mère produit `BAP-…` pour un baptême
  et `MAR-…` pour un mariage. C'est du **polymorphisme**.
- **Compteur par paroisse ET par année** : `filter(paroisse=…, date__year=annee)`. Chaque
  paroisse a sa propre séquence, qui repart à 0001 chaque année. C'est fidèle à un vrai
  registre paroissial (un registre par an).
- **`.exclude(pk=self.pk)`** : lors d'une re-sauvegarde, on ne se compte pas soi-même.
- Le numéro n'est généré **que s'il est vide** (`if not self.numero_acte`) : un acte garde
  son numéro à vie même si on le modifie.

> ⚠️ Point d'honnêteté à connaître pour le jury : cette numérotation par `count()+1` n'est pas
> protégée contre deux enregistrements **simultanés** (course critique). Le garde-fou est la
> contrainte d'unicité `UniqueConstraint(paroisse, numero_acte)` en base : au pire, une insertion
> concurrente échouerait plutôt que de créer un doublon silencieux.

### `ActePersonnel` — acte rattaché à une personne

```python
class ActePersonnel(ActeBase):
    paroissien = models.ForeignKey(Paroissien, on_delete=models.PROTECT)
    class Meta(ActeBase.Meta):
        abstract = True
    def __str__(self):
        return f"{self.numero_acte} — {self.paroissien.nom_complet()}"
```

- Relation **1:N** : un paroissien peut avoir plusieurs baptêmes/communions… (côté N),
  un acte pointe vers un seul paroissien (côté 1).
- `on_delete=PROTECT` : on ne supprime pas un paroissien tant qu'il figure dans un registre.
- `__str__` appelle `paroissien.nom_complet()` — une méthode métier de l'app `paroissiens`.

### Les cinq modèles concrets

- **`Bapteme`** (`PREFIXE = "BAP"`) : ajoute `parrain` et `marraine` (facultatifs, `blank=True`).
- **`Communion`** (`"COM"`), **`Confirmation`** (`"CONF"`), **`Funerailles`** (`"FUN"`) :
  n'ajoutent aucun champ, juste leur préfixe et leur `Meta`.
- **`Mariage`** (`"MAR"`) hérite d'`ActeBase` directement et déclare **deux** FK vers `Paroissien` :

```python
conjoint1 = models.ForeignKey(Paroissien, on_delete=models.PROTECT, related_name="mariages_conjoint1")
conjoint2 = models.ForeignKey(Paroissien, on_delete=models.PROTECT, related_name="mariages_conjoint2")
temoins = models.CharField(max_length=300, blank=True)
```

Les **`related_name` distincts** sont obligatoires : sans eux, Django ne saurait pas construire
`paroissien.mariages_conjoint1` vs `mariages_conjoint2` (deux FK vers le même modèle).

Chaque modèle concret déclare :

```python
constraints = [
    models.UniqueConstraint(fields=["paroisse", "numero_acte"], name="unique_numero_acte_bapteme")
]
```

C'est une **contrainte d'intégrité composite** : le couple (paroisse, numéro d'acte) est unique.
Deux paroisses peuvent chacune avoir un `BAP-2026-0001`, mais jamais deux fois dans la même paroisse.
Et chaque modèle a un `get_absolute_url()` renvoyant vers sa vue détail (utilisé après création).

### `MentionMarginale` — la mise à jour perpétuelle de l'acte de baptême

```python
class MentionMarginale(models.Model):
    TYPE_CHOICES = [
        ("mariage", "Mariage"), ("ordination", "Ordination"),
        ("deces", "Décès"), ("autre", "Autre"),
    ]
    bapteme = models.ForeignKey(Bapteme, related_name="mentions_marginales", on_delete=models.CASCADE)
    type_mention = models.CharField(max_length=20, choices=TYPE_CHOICES)
    date = models.DateField()
    reference = models.CharField(max_length=200, blank=True)
    paroisse = models.ForeignKey(Paroisse, on_delete=models.PROTECT)
    objects = creer_manager_paroisse()
```

**Pourquoi cette entité existe (droit canonique) — à savoir expliquer au jury :**

En droit canonique, l'**acte de baptême est le document d'état civil de référence du fidèle**.
Quand une personne se marie, est ordonnée prêtre, prononce des vœux religieux ou décède, on
n'ouvre pas un nouveau dossier : on ajoute une **mention en marge** de son acte de baptême
d'origine. L'acte de baptême devient ainsi une sorte de « fil de vie » sacramentel, mis à jour
**toute la vie durant**. C'est ce que reproduit `MentionMarginale`.

Détails techniques :

- Relation **1:N** : un baptême a plusieurs mentions (`related_name="mentions_marginales"`),
  chaque mention appartient à un seul baptême.
- **`on_delete=models.CASCADE`** ici (et non PROTECT) : c'est cohérent — une mention n'a aucun
  sens sans son acte de baptême, donc si l'acte disparaît, ses mentions disparaissent avec lui.
- `type_mention` avec `choices` : contrainte de domaine (valeurs limitées à la liste).
- `get_type_mention_display()` (méthode Django auto-générée par `choices`) est utilisée dans le template
  pour afficher « Mariage » plutôt que `mariage`.

---

## `forms.py` — saisie filtrée par paroisse

Chemin : [apps/sacrements/forms.py](../apps/sacrements/forms.py)

```python
class _FormActeParoissienMixin:
    champs_paroissien = ["paroissien"]
    def __init__(self, *args, paroisse=None, **kwargs):
        super().__init__(*args, **kwargs)
        if paroisse is not None:
            queryset = Paroissien.objects.filter(paroisse=paroisse)
            for nom_champ in self.champs_paroissien:
                self.fields[nom_champ].queryset = queryset
        self.fields["date"].widget = forms.DateInput(attrs={"type": "date"})
```

À défendre : ce mixin **restreint la liste déroulante** des paroissiens à ceux de la paroisse
courante. Sans ça, un secrétaire pourrait (via le menu déroulant) enregistrer un baptême pour
un paroissien d'une **autre** paroisse — fuite de données inter-tenant. Le `MariageForm` surcharge
`champs_paroissien = ["conjoint1", "conjoint2"]` pour filtrer les deux conjoints.

Il transforme aussi le champ date en `<input type="date">` (sélecteur natif du navigateur).

Les cinq `*Form` sont des `ModelForm` : ils déduisent leurs champs du modèle. On remarque que
`numero_acte`, `paroisse` et `date_enregistrement` **ne sont pas** dans `fields` — ils sont
remplis automatiquement (numéro par `save()`, paroisse par la vue, horodatage par `auto_now_add`).

`MentionMarginaleForm` n'expose que `type_mention`, `date`, `reference` : le `bapteme` et la
`paroisse` sont posés par la vue (voir plus bas), jamais choisis par l'utilisateur.

---

## `views.py` — le contrôleur (MVT, critère 6)

Chemin : [apps/sacrements/views.py](../apps/sacrements/views.py)

### Constantes de rôles

```python
ROLES_LECTURE = ("Secrétaire", "Lecteur")
ROLES_ECRITURE = ("Secrétaire",)
```

- **Lecture** (listes, détails, certificats) : Secrétaire + Lecteur.
- **Écriture** (créer, modifier, ajouter une mention) : Secrétaire seul.
- Le **Curé** et le **superadmin** passent toujours (logique dans `RoleRequisMixin`, voir §rôles).
- Le **Trésorier** n'a aucun rôle ici → 403 sur tout le module (il ne gère que les finances).

### Les mixins réutilisés (POO côté vues)

- **`ActePersonnelMixin`** : factorise les vues des 4 registres personnels (Baptême, Communion,
  Confirmation, Funérailles) qui partagent les **mêmes trois gabarits** génériques
  (`acte_liste/detail/form.html`). Chaque vue ne fait que fixer `type_url`, `nom_singulier`,
  `nom_pluriel`, injectés dans le contexte du template.
- **`FiltrageParoisseMixin`** (de `apps.comptes.mixins`) : filtre le queryset sur
  `request.paroisse` **et** rattache l'objet créé à la paroisse courante dans `form_valid`.
  C'est la « défense en profondeur » qui double le manager multi-tenant.
- **`RoleRequisMixin`** (de `apps.comptes.mixins`) : contrôle d'accès par rôle.
- **`CertificatMixin`** : factorise les vues certificat des actes personnels.

### Exemple : la vue liste des baptêmes

```python
class BaptemeListView(RoleRequisMixin, FiltrageParoisseMixin, ActePersonnelMixin, ListView):
    model = Bapteme
    context_object_name = "actes"
    roles_autorises = ROLES_LECTURE
    type_url, nom_singulier, nom_pluriel = "bapteme", "Baptême", "Baptêmes"

    def get_queryset(self):
        return super().get_queryset().select_related("paroissien")
```

Le `select_related("paroissien")` (critère 14) fait une **jointure SQL** : au lieu d'une requête
par ligne pour afficher le nom du paroissien (problème N+1), une seule requête ramène tout.

### La vue détail du baptême (jointures + mentions)

```python
class BaptemeDetailView(...):
    def get_queryset(self):
        return (super().get_queryset()
                .select_related("paroissien")
                .prefetch_related("mentions_marginales"))
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["formulaire_mention"] = MentionMarginaleForm()
        return context
```

C'est la seule vue détail qui `prefetch_related("mentions_marginales")` (relation 1:N inverse)
et qui injecte le formulaire d'ajout de mention dans la page.

### L'ajout d'une mention marginale

```python
class MentionMarginaleCreateView(RoleRequisMixin, View):
    roles_autorises = ROLES_ECRITURE
    def post(self, request, pk):
        bapteme = get_object_or_404(Bapteme, pk=pk, paroisse=request.user.paroisse)
        formulaire = MentionMarginaleForm(request.POST)
        if formulaire.is_valid():
            mention = formulaire.save(commit=False)
            mention.bapteme = bapteme
            mention.paroisse = request.user.paroisse
            mention.save()
            messages.success(request, "Mention marginale ajoutée.")
        else:
            messages.error(request, "La mention marginale n'a pas pu être ajoutée.")
        return redirect("sacrements:bapteme_detail", pk=bapteme.pk)
```

Points défendables :

- **`get_object_or_404(Bapteme, pk=pk, paroisse=request.user.paroisse)`** : on vérifie que le
  baptême appartient bien à la paroisse de l'utilisateur → **impossible d'ajouter une mention
  à un acte d'une autre paroisse** (isolation multi-tenant au niveau de l'action).
- **`save(commit=False)`** : on construit l'objet sans l'écrire, on lui attribue `bapteme` et
  `paroisse` (jamais fournis par le formulaire = jamais falsifiables par le client), puis on sauvegarde.

### Les certificats imprimables

Deux voies (personnels via `CertificatMixin`, mariage à part) mais même principe :

```python
class CertificatMixin(RoleRequisMixin):
    roles_autorises = ROLES_LECTURE
    def get(self, request, pk):
        acte = get_object_or_404(self.modele, pk=pk, paroisse=request.user.paroisse)
        return render(request, self.template_certificat, {"acte": acte, "type_url": self.type_url})
```

Le « PDF » n'est pas généré côté serveur : le gabarit `acte_certificat.html` propose un bouton
`window.print()`, et le navigateur permet « Imprimer → Enregistrer en PDF ». Choix simple,
sans dépendance lourde, à assumer devant le jury (rien à installer, fonctionne partout).

---

## `admin.py` — backoffice (critère 15)

Chemin : [apps/sacrements/admin.py](../apps/sacrements/admin.py)

Les six modèles sont enregistrés. Exemple représentatif :

```python
@admin.register(Bapteme)
class BaptemeAdmin(admin.ModelAdmin):
    list_display = ("numero_acte", "paroissien", "date", "celebrant", "paroisse")
    search_fields = ("numero_acte", "paroissien__nom", "paroissien__prenom")
    list_filter = ("paroisse", "date")
    list_select_related = ("paroissien", "paroisse")
    readonly_fields = ("numero_acte",)
    inlines = [MentionMarginaleInline]
```

- `list_display` / `list_filter` / `search_fields` : la checklist du critère 15.
- `list_select_related` : jointures optimisées aussi dans l'admin.
- `readonly_fields = ("numero_acte",)` : le numéro reste non modifiable même pour un admin.
- **`MentionMarginaleInline`** (`TabularInline`) : on édite les mentions **directement dans la
  page du baptême** — reflet visuel de la « marge » de l'acte.
- L'isolation multi-tenant de l'admin est portée par le **manager par défaut** (`creer_manager_paroisse`),
  puisque `ModelAdmin.get_queryset()` l'utilise.

---

## `urls.py` — routes

Chemin : [apps/sacrements/urls.py](../apps/sacrements/urls.py) — `app_name = "sacrements"`.

Schéma régulier par registre : `liste`, `creer`, `detail/<pk>`, `modifier/<pk>`, `certificat/<pk>`.
Le baptême a en plus `mentions/ajouter/<pk>` (`name="mention_marginale_creer"`). Cette régularité
permet aux templates de composer dynamiquement les noms d'URL, ex.
`{% url 'sacrements:'|add:type_url|add:'_liste' %}`.

---

## Les templates (`templates/sacrements/`)

Tous étendent `base_app.html` et réutilisent le partial `partials/_form_field.html`.

| Fichier | Rôle |
|---|---|
| `index.html` | Page d'accueil du module : cartes vers les 5 registres. |
| `acte_liste.html` | Tableau générique d'un registre personnel (N° d'acte, paroissien, date, célébrant) + pagination + état vide. Partagé par Baptême/Communion/Confirmation/Funérailles. |
| `acte_detail.html` | Fiche d'un acte personnel. **Affiche le bloc mentions marginales + le formulaire d'ajout uniquement si `type_url == "bapteme"`.** |
| `acte_form.html` | Formulaire générique création/modification (le titre change selon `object`). |
| `acte_certificat.html` | Certificat imprimable d'un acte personnel (bouton `window.print()`). |
| `mariage_liste.html` | Liste des mariages (colonne « Conjoints » = les deux noms). |
| `mariage_detail.html` | Fiche mariage (deux conjoints liés, témoins). |
| `mariage_form.html` | Formulaire mariage. |
| `mariage_certificat.html` | Certificat de mariage imprimable. |

Le mariage a ses propres gabarits parce que sa structure (deux conjoints, pas de « paroissien »
unique, pas de mentions marginales) ne rentre pas dans le gabarit générique des actes personnels.

Détail à connaître : dans `acte_detail.html`, la condition `{% if acte.parrain is not None %}`
sert à n'afficher parrain/marraine que pour le baptême (seul modèle qui a ces attributs).

---

## Tests

### [tests/test_models.py](../apps/sacrements/tests/test_models.py) — la logique métier

| Test | Ce qu'il vérifie |
|---|---|
| `test_numero_acte_genere_automatiquement` | Un baptême créé sans numéro reçoit `BAP-2026-0001`. |
| `test_numero_acte_incremente_par_annee_et_par_paroisse` | Deux baptêmes de la même paroisse → `0001` puis `0002` ; un baptême d'une **autre** paroisse repart à `BAP-2026-0001` (compteur indépendant par paroisse). C'est le test clé du multi-tenant sur la numérotation. |
| `test_mariage_relie_deux_paroissiens_distincts` | Un mariage porte bien `conjoint1`/`conjoint2` et obtient `MAR-2026-0001`. |
| `test_mention_marginale_rattachee_a_un_bapteme` | Une mention créée figure dans `bapteme.mentions_marginales.all()` et son `__str__` vaut `"Mariage — <bapteme>"`. |

### [tests/test_vues.py](../apps/sacrements/tests/test_vues.py) — permissions et isolation

| Test | Ce qu'il vérifie |
|---|---|
| `test_secretaire_peut_enregistrer_un_bapteme` | POST du secrétaire → redirection 302, baptême créé, numéro généré, rattaché à la bonne paroisse. |
| `test_tresorier_n_a_pas_acces_au_registre_des_baptemes` | Le Trésorier reçoit un **403** sur la liste (contrôle de rôle). |
| `test_certificat_de_bapteme_accessible_en_lecture` | Le Lecteur ouvre le certificat (200), le numéro d'acte et le mot « Certificat » y figurent. |
| `test_ajout_mention_marginale` | POST du secrétaire → 302 et `bapteme.mentions_marginales.count() == 1`. |
| `test_isolation_multi_tenant_sur_le_registre_des_baptemes` | Un secrétaire ne voit **pas** dans sa liste un baptême d'une autre paroisse (le nom « Kalonji » est absent de la réponse). |

---

## Questions probables du jury & réponses

**1. Comment sont générés les numéros d'actes, et pourquoi ce format ?**
Dans `ActeBase.save()`, si `numero_acte` est vide, on appelle `generer_numero_acte()` qui compte
les actes du **même type**, de la **même paroisse** et de la **même année**, +1, et formate
`PREFIXE-ANNÉE-NNNN` (ex. `BAP-2026-0001`). Ça reproduit un registre paroissial réel : une
séquence par sacrement, par paroisse, qui repart chaque année.

**2. Que se passe-t-il si deux baptêmes sont enregistrés exactement en même temps ?**
La numérotation par `count()+1` a une course critique théorique. Le filet de sécurité est la
`UniqueConstraint(paroisse, numero_acte)` en base : une collision provoquerait une erreur
d'intégrité plutôt qu'un doublon silencieux. Pour un secrétariat mono-utilisateur, le risque est nul.

**3. Qu'est-ce qu'une mention marginale et pourquoi un modèle à part ?**
En droit canonique, l'acte de baptême est le document de référence du fidèle ; les événements
ultérieurs (mariage, ordination, décès) s'inscrivent **en marge** de cet acte, à vie. `MentionMarginale`
modélise ça : relation 1:N vers `Bapteme`, avec `type_mention`, `date`, `reference`. On met à jour
un acte existant plutôt que d'en créer un nouveau.

**4. Pourquoi `on_delete=PROTECT` sur `paroisse` et `paroissien`, mais `CASCADE` sur `bapteme` de la mention ?**
PROTECT : on refuse de supprimer une paroisse ou un paroissien encore référencé dans un registre —
un acte ne doit jamais devenir orphelin. CASCADE : une mention marginale n'a aucun sens sans son
acte de baptême, donc elle doit disparaître avec lui.

**5. Pourquoi deux `related_name` sur le Mariage ?**
`conjoint1` et `conjoint2` sont deux FK vers le **même** modèle `Paroissien`. Sans `related_name`
distincts, Django ne pourrait pas nommer les deux relations inverses. On a donc
`mariages_conjoint1` et `mariages_conjoint2`.

**6. Où se joue l'isolation multi-tenant dans cette app ?**
À trois niveaux : (a) le **manager** `creer_manager_paroisse()` filtre par défaut sur la paroisse
courante — protège aussi l'admin ; (b) `FiltrageParoisseMixin` filtre explicitement le queryset
des vues (défense en profondeur) et rattache l'objet créé à la paroisse ; (c) les formulaires
restreignent la liste des paroissiens sélectionnables, et `get_object_or_404(..., paroisse=...)`
verrouille les actions unitaires. Le test `test_isolation_multi_tenant...` le prouve.

**7. Comment respectez-vous le pattern MVT ?**
Model = `models.py` (données + règle de numérotation). View = `views.py` (contrôleur : permissions,
querysets, contexte). Template = `templates/` (présentation pure). Aucune requête SQL n'est écrite
dans un template, aucune balise HTML dans un modèle.

**8. Comment fonctionnent les certificats imprimables ?**
Une vue certificat (`CertificatMixin` / `MariageCertificatView`) récupère l'acte de la bonne
paroisse et rend un gabarit `*_certificat.html` avec un bouton `window.print()`. Le navigateur
gère l'export PDF. Pas de bibliothèque PDF côté serveur : simple, portable, sans dépendance.

**9. Pourquoi une hiérarchie de modèles abstraits plutôt que cinq modèles indépendants ?**
Pour ne pas dupliquer les champs communs (numéro, date, lieu, célébrant, paroisse) ni la logique
de numérotation. `ActeBase` (abstract) porte tout ça une seule fois ; `type(self)` dans
`generer_numero_acte()` rend le comportement polymorphe pour chaque sous-classe. C'est l'illustration
directe du critère POO.

**10. Comment évitez-vous le problème N+1 dans les listes et fiches ?**
Les querysets utilisent `select_related("paroissien")` (et `select_related("conjoint1", "conjoint2")`
pour les mariages) pour ramener les données liées en une jointure, et la fiche baptême ajoute
`prefetch_related("mentions_marginales")` pour la relation 1:N inverse. L'admin fait pareil avec
`list_select_related`.
