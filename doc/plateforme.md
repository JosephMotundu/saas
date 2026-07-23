# App `plateforme` — l'espace du superadmin (côté éditeur du SaaS)

## Rôle de l'application

`ParoisseConnect` est un SaaS **multi-tenant** : une seule instance sert
plusieurs paroisses, chaque paroisse (`comptes.Paroisse`) étant un *tenant*
dont les données sont isolées des autres (voir le §1 et le §4 du
[CLAUDE.md](../CLAUDE.md)). À l'intérieur d'une paroisse, ce sont le Curé, le
Secrétaire, le Trésorier et le Lecteur qui travaillent.

L'app `plateforme` est **l'autre côté du produit** : l'espace de
l'**éditeur du SaaS**, réservé au **superadmin** de l'instance. Là où un Curé
ne voit et ne gère **que sa paroisse**, le superadmin **supervise toutes les
paroisses** : il les liste, consulte leur fiche, les suspend ou les réactive,
les supprime définitivement, réinitialise le mot de passe d'un membre en
difficulté, et édite la « vitrine » (le contenu marketing de la page d'accueil
publique).

Point d'architecture important : **cette app n'a pas de `models.py`**. Elle
n'introduit aucune table nouvelle. Elle est purement une couche de *vues +
services + templates* qui **agit sur les modèles des autres apps** :
`comptes.Paroisse`, `comptes.Utilisateur`, `comptes.Abonnement`,
`core.ContenuVitrine`, et l'ensemble des registres métier
(`paroissiens`, `sacrements`, `celebrations`, `finances`, `communication`)
lorsqu'il faut supprimer une paroisse entière.

L'app est montée sous le préfixe `plateforme/` dans les URLs racines :

```python
# config/urls.py
path("plateforme/", include("apps.plateforme.urls")),
```

et déclarée avec un label court dans [apps.py](../apps/plateforme/apps.py) :

```python
class PlateformeConfig(AppConfig):
    name = "apps.plateforme"
    label = "plateforme"
    verbose_name = "Plateforme"
```

---

## Critères du jury démontrés ici

| Critère (§3 du brief) | Où, dans cette app |
|---|---|
| **Architecture multi-tenant (§4)** — supervision *transverse* | Le superadmin a `paroisse = None`. Le middleware met alors `request.paroisse = None`, et les managers multi-tenant **ne filtrent plus** : le superadmin voit toutes les paroisses (voir la section « Comment le superadmin échappe au filtrage »). Les vues de liste/détail interrogent explicitement `Paroisse.objects`, `Utilisateur.objects.filter(paroisse=...)`, etc. |
| **Rôles & permissions (§7)** | [mixins.py](../apps/plateforme/mixins.py) : `SuperuserRequisMixin` réserve **toute** l'app au superadmin. Aucun rôle de paroisse (Curé compris) n'y accède — testé (renvoi `403`). |
| **Architecture MVC / MVT (§6)** | Séparation nette : **Modèles** dans d'autres apps, **Vues** (contrôleurs) dans [views.py](../apps/plateforme/views.py) via des CBV Django, **Templates** dans `templates/plateforme/`. La logique lourde est déportée dans [services.py](../apps/plateforme/services.py). |
| **POO (§9)** | Vues basées classes (`ListView`, `DetailView`, `UpdateView`, `View`), mixin réutilisable, et **couche `services/`** (`supprimer_paroisse`) pour une opération qui dépasse un simple modèle. |
| **Transactions (§14)** | `supprimer_paroisse` est décorée `@transaction.atomic` : la suppression complète d'un tenant est atomique (tout ou rien). |
| **Optimisation des requêtes (§14)** | `select_related("abonnement")`, `prefetch_related("groups")`, et `annotate(Count(...))` pour compter utilisateurs/paroissiens en une requête. |
| **CRUD & contraintes d'intégrité (§1)** | Les FK vers `Paroisse` sont en `on_delete=PROTECT` ; `supprimer_paroisse` respecte cet ordre de suppression. |
| **Tests (§11)** | [tests/test_paroisses.py](../apps/plateforme/tests/test_paroisses.py) et [tests/test_vitrine.py](../apps/plateforme/tests/test_vitrine.py) couvrent permissions, suspension, suppression atomique, isolation entre paroisses, réinitialisation de mot de passe, singleton vitrine. |

---

## Comment le superadmin échappe au filtrage multi-tenant

C'est le point le plus subtil de l'app, à bien maîtriser pour la soutenance.

1. Un `Utilisateur` normal appartient à une paroisse (FK `paroisse`). Le
   **superadmin, lui, a `paroisse = None`** (il est créé par
   `create_superuser` sans paroisse).

2. À chaque requête, `ParoisseCouranteMiddleware`
   ([comptes/middleware.py](../apps/comptes/middleware.py)) lit
   `request.user.paroisse` et le place dans une `ContextVar` :

   ```python
   paroisse = getattr(utilisateur, "paroisse", None)  # None pour le superadmin
   ...
   request.paroisse = paroisse
   jeton = definir_paroisse_courante(paroisse)
   ```

3. Les managers par défaut des modèles métier filtrent sur cette `ContextVar`
   — **mais s'effacent quand elle vaut `None`**
   ([comptes/managers.py](../apps/comptes/managers.py)) :

   ```python
   def de_la_paroisse_courante(self):
       paroisse = obtenir_paroisse_courante()
       if paroisse is None:
           return self          # <- aucun filtrage : tout est visible
       return self.filter(**{champ_paroisse: paroisse})
   ```

Conséquence : pour le superadmin, `paroisse_courante` vaut `None`, donc
`Paroisse.objects.all()`, `Utilisateur.objects.filter(paroisse=...)`, etc.
renvoient **les données de toutes les paroisses**. Le superadmin ne
« contourne » pas une sécurité par une astuce : c'est le mécanisme
multi-tenant lui-même qui, par conception, ne restreint pas un compte sans
paroisse.

Le middleware assure aussi qu'une paroisse **suspendue** (`est_active = False`)
déconnecte immédiatement ses membres — ce qui donne tout son effet à
l'action « Suspendre » du superadmin, même sur une session déjà ouverte.

---

## Fichier par fichier

### [mixins.py](../apps/plateforme/mixins.py) — le verrou d'accès

Rôle : réserver **chaque vue** de l'app au superadmin.

```python
class SuperuserRequisMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser
```

- `LoginRequiredMixin` : impose d'être connecté (sinon redirection login).
- `UserPassesTestMixin` : exige que `test_func()` soit vrai, sinon **HTTP 403**.
- `test_func` ne teste **que** `is_superuser`.

À comparer avec `RoleRequisMixin` de l'app comptes
([comptes/mixins.py](../apps/comptes/mixins.py)), où le Curé et le superadmin
passent toujours, et où les autres rôles dépendent de `roles_autorises`. Ici,
au contraire, **aucun rôle de paroisse ne suffit** : un Curé qui tente
d'atteindre `/plateforme/` reçoit un 403. C'est exactement ce que vérifient
les tests `test_seul_le_superadmin_...`.

Le docstring l'explicite : « la plateforme supervise toutes les paroisses, un
Curé n'en gère qu'une ».

---

### [views.py](../apps/plateforme/views.py) — les contrôleurs

Toutes les vues héritent d'abord de `SuperuserRequisMixin` (le verrou), puis
d'une classe générique Django. Détail vue par vue.

#### `ParoisseListView` (ListView) — la liste de toutes les paroisses

Route : `""` → `plateforme:paroisse_liste` (page d'accueil de la plateforme).

```python
def get_queryset(self):
    return (
        Paroisse.objects.select_related("abonnement")
        .annotate(
            nombre_utilisateurs=Count("utilisateurs", distinct=True),
            nombre_paroissiens=Count("paroissiens", distinct=True),
        )
        .order_by("nom")
    )
```

- `select_related("abonnement")` : joint l'abonnement (relation 1:1) en une
  requête, pour afficher l'offre sans requête supplémentaire par ligne (§14).
- `annotate(Count(...))` : calcule directement en base le nombre
  d'utilisateurs et de paroissiens de chaque paroisse (`distinct=True` évite le
  gonflement dû à la double jointure). Ces annotations alimentent les colonnes
  « Utilisateurs » et « Paroissiens » du tableau.
- Aucun filtrage par paroisse : on liste bien **toutes** les paroisses.

#### `ParoisseDetailView` (DetailView) — la fiche d'une paroisse

Route : `paroisses/<int:pk>/` → `plateforme:paroisse_detail`.

`get_context_data` enrichit la fiche avec, pour la paroisse consultée :

```python
context["membres"] = (
    Utilisateur.objects.filter(paroisse=paroisse)
    .prefetch_related("groups")
    .order_by("username")
)
context["nombre_paroissiens"] = Paroissien.objects.filter(paroisse=paroisse).count()
context["nombre_actes_sacrements"] = sum(
    modele.objects.filter(paroisse=paroisse).count()
    for modele in (Bapteme, Communion, Confirmation, Funerailles, Mariage)
)
context["nombre_dons"] = Don.objects.filter(paroisse=paroisse).count()
```

- La liste des **membres** (comptes) de la paroisse, avec `prefetch_related`
  sur les groupes pour afficher les rôles sans requête par membre.
- Trois compteurs (paroissiens, actes sacramentels tous registres confondus,
  dons) servant de tableau de bord synthétique.
- Le template offre les actions : suspendre/réactiver, supprimer,
  réinitialiser le mot de passe d'un membre.

#### `ParoisseBasculerActiveView` (View) — suspendre / réactiver (réversible)

Route : `paroisses/<int:pk>/basculer-active/` (POST uniquement) →
`plateforme:paroisse_basculer_active`.

```python
def post(self, request, pk):
    paroisse = get_object_or_404(Paroisse, pk=pk)
    paroisse.est_active = not paroisse.est_active
    paroisse.save(update_fields=["est_active"])
    etat = "réactivée" if paroisse.est_active else "suspendue"
    messages.success(request, f"Paroisse {paroisse.nom} {etat}.")
    return redirect("plateforme:paroisse_detail", pk=paroisse.pk)
```

- Un simple **bascule** du booléen `est_active` (défini sur le modèle
  `Paroisse`, [comptes/models.py](../apps/comptes/models.py)).
- `update_fields=["est_active"]` : n'écrit que cette colonne.
- **Réversible** et **sans perte de données** : c'est l'inverse de la
  suppression. Combiné au middleware, décocher `est_active` déconnecte
  aussitôt les membres de la paroisse.
- POST + `csrf_token` (dans le template) : une action qui modifie l'état ne
  passe jamais par un GET.

#### `ParoisseSupprimerView` (View) — suppression définitive

Route : `paroisses/<int:pk>/supprimer/` → `plateforme:paroisse_supprimer`.

Vue à deux temps (GET affiche la confirmation, POST exécute) :

- `get` : affiche la page de confirmation, avec les compteurs de ce qui sera
  perdu (comptes, paroissiens, actes, dons) et le formulaire de confirmation.
- `post` : valide `ParoisseSupprimerForm` ; si le nom retapé ne correspond
  pas, réaffiche le formulaire avec l'erreur ; sinon appelle le service
  `supprimer_paroisse(paroisse)` et redirige vers la liste.

```python
def post(self, request, pk):
    paroisse = self.get_paroisse(pk)
    form = ParoisseSupprimerForm(request.POST, paroisse=paroisse)
    if not form.is_valid():
        return render(request, self.template_name, self.get_context_data(paroisse, form=form))
    nom = paroisse.nom
    supprimer_paroisse(paroisse)
    messages.success(request, f"Paroisse {nom} et toutes ses données ont été supprimées.")
    return redirect("plateforme:paroisse_liste")
```

Le docstring souligne le contraste avec la suspension : ici l'action est
**définitive et irréversible**, d'où la double barrière (page dédiée +
retaper le nom exact).

#### `MembreReinitialiserMotDePasseView` (View) — dépannage d'un membre

Route : `membres/<int:pk>/reinitialiser-mot-de-passe/` (POST) →
`plateforme:membre_reinitialiser_mot_de_passe`.

```python
def post(self, request, pk):
    membre = get_object_or_404(Utilisateur, pk=pk, paroisse__isnull=False)
    mot_de_passe_temporaire = secrets.token_urlsafe(9)
    membre.set_password(mot_de_passe_temporaire)
    membre.save()
    return render(request, "plateforme/membre_mot_de_passe_reinitialise.html",
                  {"membre": membre, "mot_de_passe_temporaire": mot_de_passe_temporaire})
```

- `get_object_or_404(..., paroisse__isnull=False)` : on ne peut réinitialiser
  que le compte d'un **membre d'une paroisse** — pas un autre superadmin
  (dont `paroisse` est `NULL`). Garde-fou de sécurité.
- `secrets.token_urlsafe(9)` : génère un mot de passe temporaire
  cryptographiquement solide.
- `set_password(...)` : le mot de passe est **haché** (jamais stocké en
  clair — critère §3 « mot de passe haché »).
- Le mot de passe temporaire est affiché **une seule fois** (à transmettre au
  membre), puis n'est plus récupérable, comme le rappelle le template.

#### `VitrineModifierView` (UpdateView) — éditer la page d'accueil publique

Route : `vitrine/` → `plateforme:vitrine_modifier`.

```python
class VitrineModifierView(SuperuserRequisMixin, UpdateView):
    form_class = ContenuVitrineForm
    template_name = "plateforme/vitrine_modifier.html"
    success_url = reverse_lazy("plateforme:vitrine_modifier")

    def get_object(self, queryset=None):
        return ContenuVitrine.charger()

    def form_valid(self, form):
        messages.success(self.request, "Page d'accueil mise à jour.")
        return super().form_valid(form)
```

- `get_object` renvoie **le singleton** `ContenuVitrine.charger()` : il n'y a
  qu'une seule ligne de contenu vitrine pour toute l'instance (voir
  [core/models.py](../apps/core/models.py)). L'`UpdateView` édite donc
  toujours la même instance, sans `pk` dans l'URL.
- La modification se répercute immédiatement sur la page d'accueil publique
  (`core:accueil`), ce que vérifie un test.

---

### [forms.py](../apps/plateforme/forms.py) — les formulaires

#### `ContenuVitrineForm` (ModelForm)

```python
class ContenuVitrineForm(forms.ModelForm):
    class Meta:
        model = ContenuVitrine
        fields = ["titre_hero", "accroche_hero", "image_hero", "titre_cta", "texte_cta"]
        widgets = {"accroche_hero": forms.Textarea(attrs={"rows": 4})}
```

- ModelForm adossé au modèle `ContenuVitrine` : expose les champs éditables du
  bandeau « hero » de l'accueil (titre, accroche, image, titre et texte de
  l'appel à l'action). Les cartes de fonctionnalités de l'accueil restent
  fixes (précisé dans le template).

#### `ParoisseSupprimerForm` (Form) — le dernier garde-fou

```python
class ParoisseSupprimerForm(forms.Form):
    confirmation = forms.CharField(label="Nom de la paroisse, pour confirmer")

    def __init__(self, *args, paroisse=None, **kwargs):
        self.paroisse = paroisse
        super().__init__(*args, **kwargs)

    def clean_confirmation(self):
        valeur = self.cleaned_data["confirmation"]
        if valeur.strip() != self.paroisse.nom:
            raise forms.ValidationError("Le nom saisi ne correspond pas à celui de la paroisse.")
        return valeur
```

- Un formulaire simple (pas un ModelForm) : un seul champ `confirmation`.
- La paroisse ciblée est injectée au constructeur (`paroisse=...`), pour que
  `clean_confirmation` puisse comparer.
- `clean_confirmation` refuse tant que l'utilisateur n'a pas **retapé le nom
  exact** (après `strip()`). C'est le motif « type the name to confirm »
  classique des actions destructrices. Testé
  (`test_supprimer_une_paroisse_exige_de_retaper_son_nom`).

---

### [services.py](../apps/plateforme/services.py) — la couche métier (POO §9, transaction §14)

Rôle : héberger la logique qui dépasse une simple vue ou un simple modèle. Ici,
une seule fonction, centrale.

```python
@transaction.atomic
def supprimer_paroisse(paroisse):
    RecuFiscal.objects.filter(don__paroisse=paroisse).delete()
    Don.objects.filter(paroisse=paroisse).delete()
    IntentionMesse.objects.filter(paroisse=paroisse).delete()
    Celebration.objects.filter(paroisse=paroisse).delete()
    for modele in (Bapteme, Communion, Confirmation, Funerailles, Mariage):
        modele.objects.filter(paroisse=paroisse).delete()
    Annonce.objects.filter(paroisse=paroisse).delete()
    Paroissien.objects.filter(paroisse=paroisse).delete()
    Famille.objects.filter(paroisse=paroisse).delete()
    Utilisateur.objects.filter(paroisse=paroisse).delete()
    paroisse.delete()
```

Points à défendre devant le jury :

- **`@transaction.atomic` (§14)** : toutes les suppressions se font dans **une
  seule transaction**. En cas d'erreur en cours de route, un rollback annule
  tout : soit la paroisse disparaît **entièrement**, soit **rien** ne change.
  Pas d'état intermédiaire incohérent (une paroisse à moitié effacée).

- **Pourquoi supprimer explicitement, registre par registre ?** Chaque FK vers
  `Paroisse` est volontairement `on_delete=PROTECT` (contrainte d'intégrité,
  §1). Un `paroisse.delete()` direct lèverait donc un `ProtectedError`. Ce
  `PROTECT` est un garde-fou **voulu** contre les suppressions accidentelles en
  cascade ; la seule façon de supprimer un tenant est de passer par cette
  fonction, qui vide chaque table dans le bon ordre.

- **L'ordre respecte les autres contraintes PROTECT internes.** On supprime
  d'abord ce qui dépend d'autre chose : les `RecuFiscal` avant leurs `Don`
  (relation 1:1 protégée), les `IntentionMesse` avant leur `Celebration`.
  Puis les `Paroissien` avant leur `Famille`. Enfin les utilisateurs, puis la
  paroisse elle-même.

- **Placer ça dans un service (POO §9)** plutôt que dans la vue : la logique
  est testable isolément et réutilisable (une future commande de gestion
  pourrait l'appeler). La vue reste un mince contrôleur.

---

### [urls.py](../apps/plateforme/urls.py) — le routage

```python
app_name = "plateforme"

urlpatterns = [
    path("", views.ParoisseListView.as_view(), name="paroisse_liste"),
    path("paroisses/<int:pk>/", views.ParoisseDetailView.as_view(), name="paroisse_detail"),
    path("paroisses/<int:pk>/basculer-active/", views.ParoisseBasculerActiveView.as_view(), name="paroisse_basculer_active"),
    path("paroisses/<int:pk>/supprimer/", views.ParoisseSupprimerView.as_view(), name="paroisse_supprimer"),
    path("membres/<int:pk>/reinitialiser-mot-de-passe/", views.MembreReinitialiserMotDePasseView.as_view(), name="membre_reinitialiser_mot_de_passe"),
    path("vitrine/", views.VitrineModifierView.as_view(), name="vitrine_modifier"),
]
```

- `app_name = "plateforme"` : namespace des URLs (`plateforme:paroisse_liste`…).
- URLs RESTful lisibles : ressource `paroisses/<pk>/` et ses actions en
  sous-chemins ; `membres/<pk>/...` ; `vitrine/`.

---

### Templates

Toutes les pages étendent [base_plateforme.html](../templates/base_plateforme.html),
la coquille propre à l'espace superadmin.

| Fichier | Rôle |
|---|---|
| [base_plateforme.html](../templates/base_plateforme.html) | Gabarit de l'espace plateforme (hérite de `base.html`). Barre supérieure « ParoisseConnect — Plateforme » avec deux onglets : **Paroisses** et **Vitrine** (état actif calculé sur `request.resolver_match`), l'utilisateur connecté et le bouton de déconnexion. Inclut le bandeau des messages flash. |
| [paroisse_liste.html](../apps/plateforme/templates/plateforme/paroisse_liste.html) | Tableau « registre » de toutes les paroisses : nom (lien vers la fiche), diocèse, offre (`abonnement.get_offre_display`), statut (Suspendue / Abonnement annulé / Active), et les compteurs annotés utilisateurs/paroissiens. État vide géré. |
| [paroisse_detail.html](../apps/plateforme/templates/plateforme/paroisse_detail.html) | Fiche d'une paroisse : boutons suspendre/réactiver (formulaire POST) et supprimer ; informations (diocèse, adresse, statut, abonnement, date de création, lien vers la page publique) ; trois compteurs ; tableau des comptes de la paroisse (rôle via les groupes, statut actif) avec un bouton « Réinitialiser le mot de passe » par membre. |
| [paroisse_supprimer.html](../apps/plateforme/templates/plateforme/paroisse_supprimer.html) | Page de confirmation de suppression : avertissement « définitif et irréversible », compteurs de ce qui sera perdu, et le formulaire exigeant de retaper le nom exact. Bouton « Annuler » de repli. |
| [membre_mot_de_passe_reinitialise.html](../apps/plateforme/templates/plateforme/membre_mot_de_passe_reinitialise.html) | Écran affichant **une seule fois** le mot de passe temporaire généré, avec la paroisse et le nom d'utilisateur, à transmettre au membre. |
| [vitrine_modifier.html](../apps/plateforme/templates/plateforme/vitrine_modifier.html) | Formulaire d'édition du bandeau « hero » de l'accueil (encodage `multipart/form-data` pour l'image), aperçu de l'image actuelle, et lien « Voir la page d'accueil ». |

---

## Tests

### [tests/test_paroisses.py](../apps/plateforme/tests/test_paroisses.py)

Fixtures : une `paroisse` Saint Raphaël avec son `Abonnement`, un `superadmin`
(`create_superuser`), et un helper `creer_cure` (utilisateur rattaché à la
paroisse, ajouté au groupe « Curé »).

| Test | Ce qu'il vérifie |
|---|---|
| `test_seul_le_superadmin_accede_a_la_liste` | Un Curé connecté reçoit **403** sur la liste des paroisses. Le verrou `SuperuserRequisMixin` fonctionne. |
| `test_la_liste_montre_toutes_les_paroisses_avec_leurs_stats` | Le superadmin voit la paroisse (200), son nom apparaît, et l'annotation `nombre_paroissiens` vaut bien 1. Valide l'accès transverse **et** les annotations `Count`. |
| `test_suspendre_puis_reactiver_une_paroisse` | Deux POST successifs sur `basculer_active` font passer `est_active` à `False` puis de nouveau à `True`. La bascule est bien réversible. |
| `test_reinitialiser_le_mot_de_passe_d_un_membre` | Le POST renvoie 200 avec « Mot de passe temporaire », et l'ancien mot de passe du Curé ne fonctionne plus (`check_password` faux) — le mot de passe a bien été changé et haché. |
| `test_fiche_paroisse_liste_ses_membres` | La fiche détail contient le `username` du Curé : le contexte `membres` est bien peuplé. |
| `test_seul_le_superadmin_peut_supprimer_une_paroisse` | Un Curé qui tente la suppression reçoit **403** et la paroisse existe toujours. |
| `test_supprimer_une_paroisse_efface_toutes_ses_donnees` | Après avoir peuplé la paroisse (famille, paroissiens, baptême, mariage, célébration + intention, don + reçu fiscal, annonce), la suppression renvoie 302 et **plus aucune** donnée liée ne subsiste (utilisateurs, paroissiens, familles, sacrements, célébrations, intentions, dons, reçus, annonces, abonnement). Valide `supprimer_paroisse` de bout en bout. |
| `test_supprimer_une_paroisse_exige_de_retaper_son_nom` | Un mauvais nom en `confirmation` → 200 (le formulaire réaffiche l'erreur), la paroisse et son Curé sont intacts. Valide le garde-fou du formulaire. |
| `test_supprimer_une_paroisse_ne_touche_pas_les_autres` | Supprimer une paroisse laisse **intacte** une autre paroisse (« Saint Pierre ») et son Curé. Valide l'**isolation multi-tenant** : la suppression cible bien un seul tenant. |

### [tests/test_vitrine.py](../apps/plateforme/tests/test_vitrine.py)

| Test | Ce qu'il vérifie |
|---|---|
| `test_contenu_vitrine_charger_cree_une_instance_par_defaut` | `ContenuVitrine.charger()` crée l'instance si besoin, garantit qu'il n'y en a **qu'une** (`count() == 1`) et renvoie toujours la même (`pk` identique). Valide le pattern **singleton**. |
| `test_seul_le_superadmin_peut_modifier_la_vitrine` | Un Curé reçoit **403** sur `vitrine_modifier`. |
| `test_modifier_la_vitrine_se_repercute_sur_l_accueil` | Après un POST du superadmin modifiant le titre hero, la page d'accueil publique (`core:accueil`) affiche bien le « Titre personnalisé ». Valide la chaîne édition → rendu public. |

Lancer les tests de l'app :

```bash
pytest apps/plateforme/tests/
```

---

## Questions probables du jury & réponses

**1. Quelle est la différence entre le superadmin de la plateforme et le Curé
d'une paroisse ?**
Le Curé est le responsable **à l'intérieur d'un tenant** : il a accès complet à
**sa** paroisse et à rien d'autre (§7). Le superadmin est l'**éditeur du SaaS** :
il n'appartient à aucune paroisse (`paroisse = None`) et **supervise toutes**
les paroisses depuis l'app `plateforme` — il les crée/supprime, les suspend,
dépanne les mots de passe, édite la vitrine. Un Curé n'a jamais accès à
`/plateforme/` (403).

**2. Comment le superadmin échappe-t-il au filtrage multi-tenant ?**
Il n'a pas de paroisse. Le middleware met donc `request.paroisse = None` et
alimente la `ContextVar` avec `None`. Les managers multi-tenant testent cette
valeur : quand elle est `None`, `de_la_paroisse_courante()` renvoie le queryset
**sans filtre**. Le superadmin voit donc toutes les données de toutes les
paroisses — non par contournement, mais parce que le mécanisme multi-tenant, par
conception, ne restreint que les comptes rattachés à une paroisse.

**3. Pourquoi cette app n'a-t-elle pas de `models.py` ?**
Parce qu'elle n'introduit aucune donnée nouvelle : c'est une couche de
supervision. Elle agit sur des modèles définis ailleurs — `comptes.Paroisse`,
`comptes.Utilisateur`, `comptes.Abonnement`, `core.ContenuVitrine`, et les
registres métier lors d'une suppression. Séparer ces vues de supervision dans
leur propre app garde le code lisible et le verrou d'accès (superadmin) au même
endroit.

**4. Quelle est la différence entre « suspendre » et « supprimer » une
paroisse ?**
Suspendre bascule `est_active` à `False` : **réversible**, **sans perte de
données**, et grâce au middleware ça déconnecte aussitôt les membres. Supprimer
appelle `supprimer_paroisse` : **définitif et irréversible**, ça efface la
paroisse et **toutes** ses données. D'où deux barrières pour la suppression :
page de confirmation dédiée + obligation de retaper le nom exact.

**5. Pourquoi supprimer chaque table à la main dans `supprimer_paroisse`, et
pas un simple `paroisse.delete()` ?**
Parce que toutes les FK vers `Paroisse` sont en `on_delete=PROTECT` — une
contrainte d'intégrité volontaire qui empêche toute suppression accidentelle en
cascade. Un `delete()` direct lèverait un `ProtectedError`. Le service supprime
donc explicitement chaque registre, dans un ordre qui respecte aussi les
contraintes internes (reçu avant don, intention avant célébration, paroissien
avant famille), le tout dans une transaction atomique.

**6. À quoi sert `@transaction.atomic` ici concrètement ?**
Elle garantit l'atomicité de la suppression d'un tenant : si une erreur survient
au milieu (par exemple une contrainte oubliée), tout est annulé (rollback). On
n'a jamais une paroisse à moitié supprimée — soit tout part, soit rien. C'est le
critère §14 du brief, sur une opération réellement critique.

**7. Comment garantissez-vous qu'on ne supprime pas une paroisse par erreur ?**
`ParoisseSupprimerForm` impose de retaper le nom **exact** de la paroisse
(`clean_confirmation`), sur une page séparée qui affiche d'abord le volume de
données concerné. Sans le bon nom, le formulaire est invalide et la suppression
n'a pas lieu — c'est testé.

**8. La réinitialisation de mot de passe est-elle sûre ? Peut-on réinitialiser
n'importe qui ?**
Le mot de passe temporaire est généré avec `secrets.token_urlsafe` (source
cryptographique) et stocké **haché** via `set_password`, jamais en clair. Il
n'est affiché qu'une fois. Et le `get_object_or_404(..., paroisse__isnull=False)`
empêche de viser un compte sans paroisse : on ne peut réinitialiser que des
membres de paroisse, pas un autre superadmin.

**9. Pourquoi la vitrine est-elle un singleton, et pas un contenu par
paroisse ?**
La vitrine est la page d'accueil publique de **l'instance** (le site du
produit ParoisseConnect lui-même), pas la page d'une paroisse donnée. Il n'y en
a donc qu'une pour tout le SaaS. `ContenuVitrine.charger()` fait un
`get_or_create(pk=1)` : il y a toujours exactement une ligne, éditée par
l'`UpdateView` sans `pk` dans l'URL.

**10. Où est le respect du pattern MVT dans cette app ?**
Modèles : dans les autres apps (aucun ici). Vues (contrôleurs) : des CBV dans
`views.py`, minces, qui délèguent la logique lourde à `services.py`. Templates :
dans `templates/plateforme/`, purement présentation. Le verrou d'accès est
factorisé dans un mixin, les formulaires isolés dans `forms.py`. Chaque couche a
une responsabilité claire.
</content>
</invoke>
