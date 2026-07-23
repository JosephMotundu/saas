# App `finances` — dons, dépenses, offrandes et reçus fiscaux

Fiche de révision pour la soutenance. Elle documente entièrement l'application
Django [`apps/finances`](../apps/finances/), qui couvre l'étape 7 du plan de
construction (« App `finances` : dons + reçus, transaction atomique »).

## Rôle de l'application

`finances` est le **module comptable** de ParoisseConnect. Il permet au
**Trésorier** d'une paroisse de :

- enregistrer les **recettes** sous trois formes : les **dons** (dîme, offrande,
  quête…), les **offrandes de messe** (quêtes comptées) et — indirectement — les
  **offrandes des intentions de messe** (gérées dans l'app `celebrations`) ;
- enregistrer les **dépenses** (charges, entretien, salaires, charité…) ;
- émettre automatiquement un **reçu fiscal** pour chaque don ;
- consulter un **tableau financier** qui calcule le solde automatiquement,
  **séparément pour chaque devise**.

La décision produit centrale du module : **il n'y a jamais de conversion entre
devises**. Un montant en dollars et un montant en francs congolais ne
s'additionnent jamais ; le solde est calculé indépendamment pour chaque devise.

---

## Critères du jury démontrés ici

| Critère (brief §3) | Où le montrer dans le code |
|---|---|
| **§14 — Transactions atomiques** | [`services.py`](../apps/finances/services.py) : `enregistrer_don_avec_recu` décoré `@transaction.atomic` crée le `Don` **et** son `RecuFiscal` ou rien. Test : `test_echec_de_creation_du_recu_annule_le_don`. |
| **§14 — Jointures / optimisation** | `select_related("paroissien")` dans `DonListView`, `select_related("paroissien", "recu_fiscal")` dans `DonDetailView`, `list_select_related` dans l'admin. Agrégations en base (`Sum`, `values().annotate()`) dans le service. |
| **§1 — CRUD + contraintes d'intégrité** | 4 modèles ; `UniqueConstraint` sur `RecuFiscal.don` ; `DecimalField` pour l'argent ; `on_delete=PROTECT`. |
| **§9 — POO** | Couche `services/` réutilisable ; méthodes métier sur les modèles (`montant_affiche`, `generer_numero`, `save` surchargé). |
| **§7 — Rôles et permissions** | `RoleRequisMixin` + `roles_autorises` : lecture pour Trésorier/Lecteur, écriture pour Trésorier seul (le Curé a toujours accès). |
| **§4 — Multi-tenant** | Manager `creer_manager_paroisse()` sur chaque modèle + `FiltrageParoisseMixin` dans les vues. Test : `test_isolation_multi_tenant_sur_les_dons`. |
| **§11 — Tests** | [`tests/test_models.py`](../apps/finances/tests/test_models.py) et [`tests/test_vues.py`](../apps/finances/tests/test_vues.py). |
| **§15 — Backoffice admin** | [`admin.py`](../apps/finances/admin.py) : `list_display`, `list_filter`, `search_fields`, inline du reçu. |

---

## Le module partagé des devises — [`apps/core/devises.py`](../apps/core/devises.py)

Avant les fichiers de `finances`, il faut comprendre ce module, car tout le reste
en dépend. Il est placé dans l'app `core` (une app **feuille**, sans dépendance
métier) pour que `finances` **et** `celebrations` s'y réfèrent **sans créer de
dépendance croisée** entre elles.

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

Deux devises seulement (contexte RDC : franc congolais et dollar). Le commentaire
en tête du fichier énonce la règle produit : « dollars et francs ne sont jamais
additionnés entre eux ; chaque montant porte donc sa devise et le solde est
calculé par devise. »

`finances/models.py` **ré-exporte** ces symboles pour compatibilité :

```python
from apps.core.devises import (  # noqa: F401 (ré-export pour compatibilité)
    DEVISE_CHOICES, SYMBOLES_DEVISE, formater_montant,
)
```

---

## [`models.py`](../apps/finances/models.py) — les 4 modèles

### `Don`

Le don d'un paroissien (ou anonyme). Champs importants :

- `paroissien` : `ForeignKey` vers `Paroissien`, **`null=True, blank=True`** →
  supporte le **don anonyme** (`help_text="Laisser vide pour un don anonyme."`),
  avec `on_delete=PROTECT` pour ne pas perdre l'historique comptable si on tente
  de supprimer un donateur.
- `montant` : **`DecimalField(max_digits=12, decimal_places=2)`** — jamais un
  `FloatField` pour de l'argent (précision décimale exacte).
- `devise` : `CharField(choices=DEVISE_CHOICES, default="CDF")`.
- `type_don` : `choices` = dîme / offrande / quête / autre.
- `mode_paiement` : espèces / mobile money / virement / chèque.
- `paroisse` : `ForeignKey` vers le **tenant** (relation 1:N Paroisse→Dons).

Manager multi-tenant : `objects = creer_manager_paroisse()`.

**Méthodes métier (POO) :**

```python
def __str__(self):
    donateur = self.paroissien.nom_complet() if self.paroissien else "Don anonyme"
    return f"{donateur} — {self.montant_affiche()} ({self.get_type_don_display()})"

def montant_affiche(self):
    return formater_montant(self.montant, self.devise)
```

`montant_affiche()` est la méthode métier réutilisée dans tous les templates et
le `__str__` : elle garantit qu'un montant est **toujours** affiché avec sa
devise, jamais un nombre nu qui prêterait à confusion. `get_absolute_url()`
pointe vers `finances:don_detail`.

### `Depense`

Symétrique du don côté sorties. Champs : `libelle`, `montant` (Decimal),
`devise`, `date`, `categorie` (7 choix : charges, entretien, liturgie, salaires,
charité, administration, autre), `mode_paiement` (**réutilise**
`Don.MODE_PAIEMENT_CHOICES` — pas de duplication), `beneficiaire` (facultatif),
`paroisse`. Mêmes méthodes `montant_affiche()` / `get_absolute_url()`.

### `OffrandeMesse`

La quête d'une messe, enregistrée par le trésorier **après comptage**. Docstring
du modèle :

> Saisie libre (pas de lien obligatoire vers une célébration) : on note le
> montant compté, sa devise et la date. Comptée dans le solde au même titre que
> les dons.

`libelle` est facultatif (`blank=True`, ex. « Quête messe dominicale »),
`mode_paiement` par défaut `especes`. C'est volontairement **découplé** des
célébrations : le trésorier saisit un total compté sans devoir rattacher chaque
pièce à une messe précise.

### `RecuFiscal` — relation 1:1 avec `Don`

```python
class RecuFiscal(models.Model):
    don = models.OneToOneField(
        Don, related_name="recu_fiscal", on_delete=models.PROTECT
    )
    numero = models.CharField(max_length=30, editable=False, blank=True)
    date_emission = models.DateField(default=timezone.now)

    objects = creer_manager_paroisse("don__paroisse")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["don"], name="unique_recu_fiscal_par_don")
        ]
```

Points à défendre :

- **`OneToOneField`** = relation **1:1** Don↔RecuFiscal (critère §1 : relations
  1:1 et 1:N). Depuis le don : `don.recu_fiscal`.
- La **`UniqueConstraint` sur `don`** double la garantie d'unicité au niveau
  base de données : un don ne peut avoir qu'un seul reçu, même si un bug tentait
  d'en créer deux. C'est une contrainte d'intégrité posée en base, pas seulement
  en Python.
- `numero` est **`editable=False`** : il n'est jamais saisi à la main, il est
  généré.
- Le modèle n'a **pas de FK `paroisse` directe** : il passe par le don. D'où le
  manager `creer_manager_paroisse("don__paroisse")` qui indique le chemin de
  jointure pour filtrer par tenant.

**Génération du numéro (méthode métier + `save` surchargé) :**

```python
def generer_numero(self):
    paroisse = self.don.paroisse
    annee = self.date_emission.year
    compte = (
        RecuFiscal.objects.filter(don__paroisse=paroisse, date_emission__year=annee)
        .exclude(pk=self.pk)
        .count()
        + 1
    )
    return f"REC-{annee}-{compte:04d}"

def save(self, *args, **kwargs):
    if not self.numero:
        self.numero = self.generer_numero()
    super().save(*args, **kwargs)
```

Le numéro est de la forme **`REC-2026-0001`** : préfixe, année, puis compteur
séquentiel **par paroisse et par année** (`{compte:04d}` = 4 chiffres avec zéros
de tête). Le `.exclude(pk=self.pk)` évite de se compter soi-même en cas de
re-sauvegarde. Le `save()` ne génère le numéro **que s'il est vide**, donc il est
figé une fois émis.

---

## [`services.py`](../apps/finances/services.py) — la couche métier (POO §9)

C'est le cœur défendable de l'app. Deux fonctions.

### `enregistrer_don_avec_recu` — la transaction atomique (§14)

```python
@transaction.atomic
def enregistrer_don_avec_recu(
    *, paroisse, montant, date, type_don, mode_paiement, devise="CDF", paroissien=None
):
    """Crée un Don et son RecuFiscal dans une même transaction : soit les
    deux existent, soit aucun (§14 du brief — opération critique)."""
    don = Don.objects.create(...)
    recu = RecuFiscal.objects.create(don=don, date_emission=date)
    return don, recu
```

- Le décorateur **`@transaction.atomic`** encadre les deux `create()` dans une
  **seule transaction SQL**. Si la création du reçu échoue (exception),
  PostgreSQL **annule (rollback)** aussi la création du don. On ne peut donc
  jamais se retrouver avec un don sans reçu — un état comptable incohérent.
- Les arguments sont **keyword-only** (`*`), ce qui empêche d'inverser
  accidentellement `montant` et `date` à l'appel.
- La vue de création délègue entièrement à ce service (voir `DonCreateView`).

### `calculer_situation_financiere` — l'agrégation par devise (§14)

C'est la fonction qui produit le tableau de bord. Elle agrège **trois sources de
recettes** et les dépenses, **par devise**, **directement en base**.

Petit utilitaire d'agrégation :

```python
def _totaux_par_devise(requete, champ_montant="montant"):
    """Renvoie {devise: total} pour une requête agrégée par devise."""
    lignes = requete.values("devise").annotate(total=Sum(champ_montant))
    return {ligne["devise"]: ligne["total"] or Decimal("0") for ligne in lignes}
```

`.values("devise").annotate(total=Sum(...))` produit un **GROUP BY devise** en
SQL : la base fait la somme, pas Python. C'est l'optimisation demandée par §14.

Les trois sources de recettes :

```python
dons = _totaux_par_devise(Don.objects.filter(paroisse=paroisse))
offrandes_messe = _totaux_par_devise(OffrandeMesse.objects.filter(paroisse=paroisse))
offrandes_intentions = _totaux_par_devise(
    IntentionMesse.objects.filter(paroisse=paroisse)
    .exclude(statut="annulee")
    .exclude(montant_offrande__isnull=True),
    champ_montant="montant_offrande",
)
depenses = _totaux_par_devise(Depense.objects.filter(paroisse=paroisse))
```

Points cruciaux à défendre :

- **Trois sources de recettes** : dons + offrandes de messe + offrandes des
  **intentions de messe** (ce dernier vient de l'app `celebrations`, d'où
  l'import de `IntentionMesse`).
- Les intentions **annulées** (`statut="annulee"`) sont **exclues** : de l'argent
  non perçu ne doit pas gonfler le solde. Les intentions sans montant
  (`montant_offrande__isnull=True`) sont aussi exclues.

Puis on construit la liste `par_devise`, **une entrée par devise ayant un
mouvement** :

```python
for code, _ in DEVISE_CHOICES:
    recettes_devise = (
        dons.get(code, Decimal("0"))
        + offrandes_messe.get(code, Decimal("0"))
        + offrandes_intentions.get(code, Decimal("0"))
    )
    depenses_devise = depenses.get(code, Decimal("0"))
    if not recettes_devise and not depenses_devise:
        continue  # devise sans aucun mouvement : on ne l'affiche pas
    par_devise.append({
        "devise": code, "libelle": ..., "symbole": ...,
        "recettes": recettes_devise,
        "depenses": depenses_devise,
        "solde": recettes_devise - depenses_devise,
        "dons": ..., "offrandes_messe": ..., "offrandes_intentions": ...,
    })
```

- Les additions se font **à l'intérieur d'une même devise** (`dons.get(code)` +
  `offrandes_messe.get(code)` + …). **Jamais** entre devises : c'est ainsi que
  « dollars et francs ne s'additionnent jamais ».
- `solde = recettes − dépenses`, par devise.
- Une devise sans aucun mouvement est **omise** (`continue`) → le tableau reste
  propre (pas de « 0 FC » inutile).
- Chaque ligne expose aussi la **ventilation par source** (`dons`,
  `offrandes_messe`, `offrandes_intentions`) affichée dans le tableau.

Enfin, la ventilation des dépenses par catégorie (encore un GROUP BY) :

```python
depenses_par_categorie = (
    Depense.objects.filter(paroisse=paroisse)
    .values("categorie", "devise")
    .annotate(total=Sum("montant"))
    .order_by("devise", "-total")
)
```

La fonction retourne `{"par_devise": [...], "depenses_par_categorie": [...]}`.

---

## [`forms.py`](../apps/finances/forms.py)

Trois `ModelForm` : `DonForm`, `DepenseForm`, `OffrandeMesseForm`. Chacun utilise
un widget HTML5 `date` (`forms.DateInput(attrs={"type": "date"})`) pour un
sélecteur de date natif.

`DonForm` a une particularité — il reçoit la paroisse en argument pour **borner
la liste des donateurs à la paroisse courante** :

```python
def __init__(self, *args, paroisse=None, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields["paroissien"].required = False
    if paroisse is not None:
        self.fields["paroissien"].queryset = Paroissien.objects.filter(paroisse=paroisse)
```

- `required = False` autorise le **don anonyme** dès le formulaire.
- Le `queryset` filtré empêche de sélectionner un paroissien d'une autre paroisse
  (défense multi-tenant au niveau du formulaire).

`DonForm.Meta.fields` n'inclut **pas** `paroisse` : elle est posée par la vue, à
partir de l'utilisateur connecté — jamais choisie par l'utilisateur.

---

## [`views.py`](../apps/finances/views.py)

En tête, la matrice des rôles :

```python
ROLES_LECTURE = ("Trésorier", "Lecteur")
ROLES_ECRITURE = ("Trésorier",)
```

- **Lecture** (listes, détails, tableau, reçu) : Trésorier **et** Lecteur.
- **Écriture** (créer un don, une dépense, une offrande) : **Trésorier seul**.
- Le **Curé** et le **superadmin** passent toujours (logique dans
  `RoleRequisMixin.test_func`).

`RoleRequisMixin` et `FiltrageParoisseMixin` viennent de
[`apps/comptes/mixins.py`](../apps/comptes/mixins.py). Le premier applique les
rôles ; le second filtre les querysets sur `request.paroisse` et rattache tout
objet créé à la paroisse courante.

Les vues notables :

- **`TableauFinancierView`** (`TemplateView`) : appelle
  `calculer_situation_financiere(self.request.paroisse)` et pose le résultat dans
  le contexte. C'est l'accueil du module.
- **`DonListView`** / **`DonDetailView`** : ajoutent `select_related(...)` pour
  éviter le problème N+1 (une requête au lieu d'une par ligne pour aller chercher
  le donateur, et le reçu au détail).
- **`DonCreateView`** : n'hérite **volontairement pas** de `CreateView`. Sa
  docstring l'explique : la création du Don **et** de son RecuFiscal passe par le
  service transactionnel.

```python
class DonCreateView(RoleRequisMixin, View):
    roles_autorises = ROLES_ECRITURE

    def post(self, request):
        form = DonForm(request.POST, paroisse=request.user.paroisse)
        if form.is_valid():
            don, recu = enregistrer_don_avec_recu(
                paroisse=request.user.paroisse,
                montant=form.cleaned_data["montant"],
                devise=form.cleaned_data["devise"],
                ...
            )
            messages.success(request, f"Don enregistré, reçu fiscal {recu.numero} émis.")
            return redirect("finances:don_detail", pk=don.pk)
        return render(request, self.template_name, {"form": form})
```

- **`DepenseCreateView`** / **`OffrandeMesseCreateView`** : `CreateView`
  classiques (pas de transaction multi-modèle), avec message de succès.
- **`RecuFiscalView`** : rend le reçu imprimable. Elle re-vérifie l'isolation
  explicitement : `get_object_or_404(Don, pk=pk, paroisse=request.user.paroisse)`.

---

## [`admin.py`](../apps/finances/admin.py) — backoffice (§15)

Les 4 modèles sont enregistrés avec `list_display`, `list_filter` (dont
`paroisse` et `devise`), `search_fields`, et `list_select_related` (optimisation
des requêtes dans l'admin, §14). `DonAdmin` embarque un **inline**
`RecuFiscalInline` (`StackedInline`) : on voit le reçu directement sur la fiche
du don, avec `numero` en `readonly` (il est généré, jamais édité).

---

## [`urls.py`](../apps/finances/urls.py)

Espace de noms `finances`. Routes : `tableau` (accueil), et pour chaque type de
mouvement le trio **liste / créer / détail** (`don_*`, `depense_*`,
`offrande_*`), plus `recu_fiscal` (`dons/<pk>/recu/`) pour le reçu imprimable.

---

## Templates — [`templates/finances/`](../apps/finances/templates/finances/)

| Fichier | Rôle |
|---|---|
| `tableau.html` | Tableau de bord : un bloc « Solde en … » **par devise** (compteurs recettes / dépenses / solde), la ventilation des recettes par source, puis les dépenses par catégorie. État vide : « Aucun mouvement financier… ». |
| `don_liste.html` | Table des dons (donateur ou « Don anonyme », montant via `montant_affiche`, type, mode, date). Bouton « Enregistrer un don ». |
| `don_detail.html` | Fiche d'un don, avec lien vers le paroissien et le numéro de reçu. |
| `don_form.html` | Formulaire de saisie. Sous-titre : « Le reçu fiscal est émis automatiquement à l'enregistrement du don. » Bouton « Enregistrer le don » (verbe actif constant, cf. brief). |
| `recu_certificat.html` | **Reçu fiscal imprimable** (`window.print()` → PDF). En-tête avec le nom de la paroisse, numéro, donateur, montant, dates. |
| `depense_liste.html` / `depense_detail.html` / `depense_form.html` | Trio CRUD des dépenses. |
| `offrande_liste.html` / `offrande_detail.html` / `offrande_form.html` | Trio CRUD des offrandes de messe. |

Tous les montants sont rendus via `{{ objet.montant_affiche }}` (méthode métier)
ou avec le symbole explicite (`{{ devise.solde }} {{ devise.symbole }}`), en
classe `numerique` (chiffres tabulaires, cf. direction artistique).

---

## Tests

### [`tests/test_models.py`](../apps/finances/tests/test_models.py) — modèles et services

| Test | Ce qu'il vérifie | Pourquoi |
|---|---|---|
| `test_don_anonyme_autorise` | Un `Don` sans `paroissien` est valide et son `__str__` contient « Don anonyme ». | Prouve le support du don anonyme (§ brief). |
| `test_service_enregistre_don_et_recu_dans_la_meme_transaction` | Le service crée don + reçu ; `recu.numero == "REC-2026-0001"`. | Le chemin nominal de la transaction et la génération du numéro. |
| `test_solde_par_devise_est_recettes_moins_depenses` | 150 USD de dons − 30 USD de dépense = solde 120 USD. | Formule du solde par devise. |
| `test_solde_agrege_dons_offrandes_messe_et_intentions` | dons 100 + offrande messe 40 + intention 15 = **155** ; l'intention **annulée** (999) est **ignorée**. | Les trois sources de recettes et l'exclusion des annulées. |
| `test_dollars_et_francs_ne_sont_jamais_additionnes` | 100 USD et 30 000 CDF donnent deux soldes distincts (`{"USD","CDF"}`), sans conversion. | La règle produit centrale. |
| `test_situation_financiere_sans_mouvement_est_vide` | `par_devise == []` sans aucun mouvement. | Le `continue` qui masque les devises inertes. |
| `test_echec_de_creation_du_recu_annule_le_don` | On force `RecuFiscal.objects.create` à lever ; après l'exception, `Don.objects.count() == 0`. | **La preuve de l'atomicité** : le rollback annule aussi le don. |

### [`tests/test_vues.py`](../apps/finances/tests/test_vues.py) — vues, permissions, isolation

| Test | Ce qu'il vérifie |
|---|---|
| `test_tresorier_peut_enregistrer_un_don_anonyme` | POST du Trésorier → 302, don anonyme créé, reçu `REC-2026-0001` généré via la vue. |
| `test_secretaire_n_a_pas_acces_aux_dons` | Un Secrétaire reçoit **403** sur la liste des dons (les finances ne le concernent pas). |
| `test_recu_fiscal_imprimable` | Un Lecteur accède au reçu (200) et le numéro apparaît dans le HTML. |
| `test_isolation_multi_tenant_sur_les_dons` | Un don d'une **autre** paroisse (montant 100) **n'apparaît pas** dans la liste du trésorier. Preuve de l'étanchéité des tenants. |

---

## Questions probables du jury & réponses

**1. Pourquoi une transaction atomique pour le don et le reçu ?**
Parce que ce sont deux écritures qui doivent être **tout ou rien**. Un don sans
reçu fiscal, ou un reçu orphelin, serait un état comptable incohérent.
`@transaction.atomic` garantit que si la seconde écriture échoue, la première est
annulée (rollback). Le test `test_echec_de_creation_du_recu_annule_le_don` le
prouve : on force l'échec du reçu et on vérifie que `Don.objects.count() == 0`.

**2. Comment gérez-vous deux devises sans fausser le solde ?**
Chaque montant (`Don`, `Depense`, `OffrandeMesse`) porte un champ `devise`. Le
service `calculer_situation_financiere` agrège **par devise**
(`.values("devise").annotate(total=Sum(...))`) et n'additionne que des montants
de **même** devise. Il produit une ligne de solde distincte par devise. Il n'y a
**aucune conversion** : c'est une décision produit (contexte RDC, taux volatil),
documentée dans `apps/core/devises.py`. Le test
`test_dollars_et_francs_ne_sont_jamais_additionnes` le vérifie.

**3. D'où viennent les recettes du solde ?**
De **trois sources** cumulées par devise : les **dons**, les **offrandes de
messe** (quêtes comptées) et les **offrandes des intentions de messe**. Ces
dernières viennent de l'app `celebrations` (`IntentionMesse.montant_offrande`) et
sont **exclues si l'intention est annulée** ou sans montant — de l'argent non
perçu ne doit pas gonfler le solde.

**4. Pourquoi le numéro de reçu est généré et pas saisi ?**
Pour garantir une séquence fiable et sans doublon. `generer_numero()` compte les
reçus de la même paroisse et de la même année, ajoute 1, et formate
`REC-{annee}-{compte:04d}` (ex. `REC-2026-0001`). Le champ est `editable=False`
et le numéro n'est fixé qu'une fois (le `save()` ne le régénère pas s'il existe
déjà). Le compteur est **par paroisse et par année**.

**5. Comment garantissez-vous qu'un don a au plus un reçu ?**
Deux niveaux. D'abord `OneToOneField` (relation 1:1). Ensuite une
`UniqueConstraint(fields=["don"])` posée en base de données : même un bug ou un
accès concurrent ne pourrait pas créer deux reçus pour un même don.

**6. Où sont les jointures et optimisations demandées (§14) ?**
`DonListView` fait `select_related("paroissien")` et `DonDetailView`
`select_related("paroissien", "recu_fiscal")` pour éviter le problème N+1.
L'admin utilise `list_select_related`. Les agrégats du service
(`values().annotate(Sum())`) sont des **GROUP BY** exécutés par PostgreSQL, pas
en Python.

**7. Un Secrétaire peut-il toucher aux finances ?**
Non. Les vues portent `roles_autorises` : lecture pour Trésorier/Lecteur,
écriture pour Trésorier seul ; le Curé a un accès complet. Un Secrétaire reçoit
**403** — vérifié par `test_secretaire_n_a_pas_acces_aux_dons`. C'est le §7 du
brief.

**8. Comment un don d'une paroisse reste-t-il invisible pour une autre ?**
Défense en profondeur. Le manager `creer_manager_paroisse()` filtre par défaut
sur la paroisse courante (posée par le middleware), et les vues re-filtrent
explicitement via `FiltrageParoisseMixin`. `RecuFiscalView` re-vérifie même la
paroisse dans le `get_object_or_404`. Le test
`test_isolation_multi_tenant_sur_les_dons` le confirme.

**9. Pourquoi `DecimalField` et pas `FloatField` pour les montants ?**
Parce que les flottants introduisent des erreurs d'arrondi inacceptables en
comptabilité. `DecimalField(max_digits=12, decimal_places=2)` stocke des décimaux
exacts, et le service manipule des `Decimal("0")` pour rester cohérent.

**10. Pourquoi `on_delete=PROTECT` presque partout ?**
Pour protéger l'historique comptable. On ne doit pas pouvoir supprimer une
paroisse, un donateur ou un don s'il est encore référencé (par un reçu, par
exemple) : `PROTECT` lève une erreur plutôt que d'effacer en cascade des écritures
financières.

**11. Pourquoi `OffrandeMesse` n'est pas rattachée à une célébration précise ?**
Décision d'usage : le trésorier compte la quête d'une messe **après** l'office et
saisit un total (montant, devise, date), sans devoir relier chaque pièce à une
célébration. Le modèle reste volontairement simple ; l'offrande est comptée dans
le solde au même titre qu'un don.

**12. Pourquoi placer les devises dans `core` et non dans `finances` ?**
Parce que `celebrations` (les intentions de messe) a aussi besoin des devises. Si
on les mettait dans `finances`, `celebrations` devrait importer `finances` — et
`finances` importe déjà `celebrations` (pour agréger les intentions). On aurait
une dépendance croisée. `core` est une app feuille sans dépendance métier : les
deux peuvent s'y référer proprement.
