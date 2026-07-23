# App `core` — vitrine publique, inscription et tableau de bord

> Fiche de révision pour la soutenance. Tout ce qui est écrit ici est vérifié
> dans le vrai code — les extraits sont copiés des fichiers, pas devinés.

## Rôle transversal de l'app

`core` est l'app **charnière** du projet. Elle ne possède presque pas de modèle
métier (les vraies entités vivent dans `comptes`, `paroissiens`, `sacrements`,
`celebrations`, `finances`, `communication`), mais elle assure trois fonctions
qui touchent toutes les autres :

1. **La vitrine publique** (pages accessibles sans connexion) : page d'accueil,
   fonctionnalités, tarifs — c'est la façade commerciale du SaaS.
2. **Le flux d'inscription self-service** : le point d'entrée par lequel un
   nouveau client crée sa **paroisse** (le *tenant*), son **abonnement** et son
   compte **Curé** administrateur, le tout en une seule transaction.
3. **Le tableau de bord** : la première page qu'un utilisateur connecté voit,
   avec des compteurs synthétiques et la carte de sa paroisse.

Elle héberge aussi un module partagé, [`devises.py`](../apps/core/devises.py),
placé ici précisément parce que `core` est une **app feuille** : elle ne dépend
d'aucune autre app métier, donc `finances` et `celebrations` peuvent y importer
les devises sans créer de dépendance croisée (voir la section dédiée plus bas).

Le libellé de l'app le résume — [apps.py](../apps/core/apps.py) :

```python
class CoreConfig(AppConfig):
    name = "apps.core"
    label = "core"
    verbose_name = "Vitrine et tableau de bord"
```

---

## Critères du jury démontrés ici

| Critère | Où le montrer dans `core` |
|--------|---------------------------|
| **6. Architecture MVT** | Séparation stricte : `models.py` (Model), templates dans `templates/core/` (Vue/Template), `views.py` en vues basées classes `TemplateView`/`FormView` (Contrôleur). Aucune logique métier dans les templates. |
| **5. Responsive design** | Toutes les pages étendent `base_public.html` ou `base_app.html` et utilisent la grille Bootstrap (`row g-4`, `col-12 col-md-4`) surchargée par le thème custom. |
| **9. POO** | Le singleton `ContenuVitrine.charger()` (méthode de classe), les vues basées classes, la composition d'adresse dans `form_valid`. |
| **14. Transactions atomiques** | L'inscription enveloppe création paroisse + abonnement + Curé dans un `transaction.atomic()`. |
| **8b. Consommation d'API externe (Nominatim)** | Le tableau de bord et la souscription appellent les endpoints de géocodage (`/api/paroisse/geocoder/`, `/api/rechercher-adresse/`, `/api/geocoder-inverse/`) et affichent le résultat sur **Leaflet**. |
| **7. Rôles & permissions** | Le tableau de bord n'affiche compteurs et sections que selon le rôle (via le context processor `navigation_par_role` de `comptes`). |
| **11. Tests** | Trois fichiers de tests : `test_inscription.py`, `test_pages_publiques.py`, `test_tableau_de_bord.py`. |
| **15. Backoffice admin** | `ContenuVitrine` est enregistré dans l'admin en mode singleton (ajout/suppression bridés). |

> Nuance à défendre honnêtement : `core` **consomme** l'API Nominatim côté
> navigateur (JavaScript Leaflet + `fetch`), mais les endpoints qui appellent
> réellement Nominatim sont définis ailleurs (app `comptes` / API). `core`
> fournit l'interface (carte, bouton « Localiser automatiquement »).

---

## Fichier par fichier

### [models.py](../apps/core/models.py) — le singleton `ContenuVitrine`

**Rôle** : rendre éditable, sans toucher au code, le bloc « hero » (titre +
accroche + image + appel à l'action) de la page d'accueil publique. Le
superadmin le modifie depuis l'admin `/plateforme/`.

C'est un **singleton** : on ne veut qu'**une seule** ligne en base (il n'y a
qu'une page d'accueil). Le patron est implémenté par une méthode de classe :

```python
class ContenuVitrine(models.Model):
    titre_hero = models.CharField("titre principal", max_length=200, default="...")
    accroche_hero = models.TextField("accroche", default="...")
    image_hero = models.ImageField("image", upload_to="vitrine/", blank=True, null=True)
    titre_cta = models.CharField("titre de l'appel à l'action", max_length=200, default="Prêt pour votre paroisse ?")
    texte_cta = models.CharField("texte de l'appel à l'action", max_length=300, default="...")

    @classmethod
    def charger(cls):
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
```

Points à défendre :

- **`charger()` force `pk=1`** : `get_or_create(pk=1)` renvoie la ligne 1 si elle
  existe, sinon la crée avec les valeurs par défaut. Résultat : la page d'accueil
  fonctionne **dès le premier affichage**, même si personne n'a rien saisi
  (les `default=...` fournissent un texte de vitrine crédible).
- Les `default` incarnent la **direction artistique** du brief (« le registre de
  votre paroisse, tenu avec la même rigueur qu'un missel relié »).
- C'est un exemple concret de **POO** : encapsuler la règle « il n'existe qu'une
  instance » dans le modèle lui-même, pas dans la vue.

### [devises.py](../apps/core/devises.py) — module partagé multi-devises

**Rôle** : centraliser la liste des devises, leurs symboles et le formatage
d'un montant. Utilisé par `finances` (dons) et `celebrations` (offrandes).

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

**POURQUOI ce code est-il dans `core` ?** (question quasi certaine du jury)

- `finances` et `celebrations` ont toutes deux besoin des mêmes devises. Si on
  mettait ces constantes dans `finances`, alors `celebrations` devrait importer
  `apps.finances` — et inversement. On créerait une **dépendance croisée**
  (couplage circulaire) entre deux apps métier.
- `core` est une **app feuille** : elle ne dépend d'aucune app métier. Les deux
  apps peuvent donc pointer vers `core.devises` sans risque de cycle d'import.
  C'est le principe de la **dépendance stable** : on dépend toujours vers ce qui
  ne bouge pas / ne dépend de rien.
- **Décision produit** documentée dans le docstring du fichier : dollars et
  francs **ne sont jamais additionnés** ; chaque montant porte sa devise, et un
  solde se calcule **par devise**. `formater_montant` sert à afficher chaque
  montant avec le bon symbole (`45 FC`, `120 $`). Le `.get(devise, devise)`
  retombe sur le code brut si la devise est inconnue — pas de plantage.

### [forms.py](../apps/core/forms.py) — le formulaire d'inscription

**Rôle** : valider les données de souscription. C'est un `forms.Form` (pas un
`ModelForm`) car il crée **plusieurs objets** (paroisse + abonnement + Curé),
pas un seul modèle.

```python
OFFRES = Abonnement.OFFRE_CHOICES

class InscriptionForm(forms.Form):
    # Paroisse — adresse découpée en champs structurés (usage RDC)
    nom_paroisse = forms.CharField(label="Nom de la paroisse", max_length=200)
    diocese = forms.CharField(label="Diocèse", max_length=200)
    ville = forms.CharField(label="Ville", max_length=100)
    commune = forms.CharField(label="Commune", max_length=100)
    quartier = forms.CharField(label="Quartier", max_length=100, required=False)
    avenue = forms.CharField(label="Avenue", max_length=200, help_text="...")
    offre = forms.ChoiceField(label="Offre choisie", choices=OFFRES)
    latitude = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=9, decimal_places=6)
    longitude = forms.DecimalField(required=False, widget=forms.HiddenInput(), max_digits=9, decimal_places=6)

    # Compte administrateur (premier Curé)
    prenom = forms.CharField(label="Prénom")
    nom = forms.CharField(label="Nom")
    email = forms.EmailField(label="Email")
    nom_utilisateur = forms.CharField(label="Nom d'utilisateur", max_length=150)
    mot_de_passe = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)
    mot_de_passe_confirmation = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)
```

Détails à défendre :

- **Adresse découpée** (ville / commune / quartier / avenue) plutôt qu'un champ
  « adresse » unique : adapté à l'usage RDC, et alimenté automatiquement par le
  géocodage inverse sur la carte (voir template `souscription.html`).
- **`latitude`/`longitude` en `HiddenInput`, `required=False`** : remplis par le
  JavaScript Leaflet ; `max_digits=9, decimal_places=6` — d'où l'arrondi à 6
  décimales fait côté JS pour éviter un rejet silencieux.
- **`OFFRES = Abonnement.OFFRE_CHOICES`** : les offres proposées sont
  exactement celles définies dans le modèle `Abonnement` — pas de duplication.

Validations métier :

```python
def clean_nom_paroisse(self):
    nom_paroisse = self.cleaned_data["nom_paroisse"]
    if Paroisse.objects.filter(nom__iexact=nom_paroisse).exists():
        raise ValidationError("Une paroisse porte déjà ce nom.")
    return nom_paroisse

def clean_nom_utilisateur(self):
    nom_utilisateur = self.cleaned_data["nom_utilisateur"]
    if Utilisateur.objects.filter(username__iexact=nom_utilisateur).exists():
        raise ValidationError("Ce nom d'utilisateur est déjà pris.")
    return nom_utilisateur

def clean(self):
    cleaned_data = super().clean()
    mot_de_passe = cleaned_data.get("mot_de_passe")
    confirmation = cleaned_data.get("mot_de_passe_confirmation")
    if mot_de_passe and confirmation and mot_de_passe != confirmation:
        self.add_error("mot_de_passe_confirmation", "Les mots de passe ne correspondent pas.")
    if mot_de_passe:
        try:
            validate_password(mot_de_passe)
        except ValidationError as erreur:
            self.add_error("mot_de_passe", erreur)
    return cleaned_data
```

- `__iexact` = unicité **insensible à la casse** sur le nom de paroisse et le nom
  d'utilisateur (« Saint Raphaël » = « saint raphaël »).
- `validate_password` réutilise les **validateurs de mot de passe de Django**
  (longueur, mot de passe courant, trop numérique…) — critère sécurité.
- La double vérification de correspondance des mots de passe se fait dans
  `clean()` (validation inter-champs).

### [views.py](../apps/core/views.py) — les 5 vues

Toutes basées sur des **vues génériques** (POO / MVT). Contrôleur mince : la
logique de validation est dans le formulaire, l'affichage dans les templates.

#### `AccueilView` (page d'accueil publique)

```python
class AccueilView(TemplateView):
    template_name = "core/accueil.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contenu"] = ContenuVitrine.charger()
        return context
```

Injecte le singleton `ContenuVitrine` pour que le template affiche le hero
éditable.

#### `FonctionnalitesView` — simple `TemplateView`, aucune logique.

#### `TarifsView` (grille des offres)

```python
class TarifsView(TemplateView):
    template_name = "core/tarifs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["offres"] = [
            (valeur, libelle, Abonnement.LIMITES[valeur]) for valeur, libelle in OFFRES
        ]
        return context
```

Compose, pour chaque offre, le triplet `(code, libellé, limites)` où `limites`
vient de `Abonnement.LIMITES` (prix, nombre max d'utilisateurs, modules
inclus…). Le template génère les cartes de tarif et met « Standard » en avant.

#### `InscriptionView` — le cœur du flux self-service

```python
class InscriptionView(FormView):
    template_name = "core/souscription.html"
    form_class = InscriptionForm

    def get_initial(self):
        initial = super().get_initial()
        offre_demandee = self.request.GET.get("offre")
        if offre_demandee in dict(OFFRES):
            initial["offre"] = offre_demandee
        return initial

    def form_valid(self, form):
        donnees = form.cleaned_data
        adresse_composee = ", ".join(
            partie
            for partie in [donnees["avenue"], donnees.get("quartier"), donnees["commune"]]
            if partie
        )
        with transaction.atomic():
            paroisse = Paroisse.objects.create(
                nom=donnees["nom_paroisse"], diocese=donnees["diocese"],
                adresse=adresse_composee, ville=donnees["ville"],
                commune=donnees["commune"], quartier=donnees.get("quartier", ""),
                avenue=donnees["avenue"], email=donnees["email"],
                latitude=donnees.get("latitude"), longitude=donnees.get("longitude"),
            )
            Abonnement.objects.create(paroisse=paroisse, offre=donnees["offre"])
            cure = Utilisateur.objects.create_user(
                username=donnees["nom_utilisateur"], password=donnees["mot_de_passe"],
                first_name=donnees["prenom"], last_name=donnees["nom"],
                email=donnees["email"], paroisse=paroisse,
            )
            cure.groups.add(Group.objects.get(name="Curé"))

        login(self.request, cure)
        messages.success(self.request, f"Bienvenue ! {paroisse.nom} est prêt.")
        return redirect("core:tableau_de_bord")
```

**Le flux d'inscription pas à pas** (à raconter au jury) :

1. **Pré-sélection de l'offre** : `get_initial()` lit `?offre=standard` dans
   l'URL. C'est ainsi que le bouton « Choisir Standard » de la page tarifs
   arrive sur le formulaire avec la bonne offre déjà cochée.
2. **Composition de l'adresse** : `avenue`, `quartier` (optionnel), `commune`
   sont recollés en une chaîne `adresse` lisible, en sautant les parties vides
   (le `if partie` élimine le quartier absent → pas de virgule orpheline).
3. **Transaction atomique** : les trois créations (paroisse → abonnement →
   Curé + affectation au groupe) sont dans un seul `transaction.atomic()`. Si
   **n'importe laquelle** échoue, **tout est annulé** (rollback). On ne se
   retrouve jamais avec une paroisse sans abonnement ou sans administrateur.
4. **`create_user`** hache le mot de passe (jamais stocké en clair) et rattache
   le Curé à sa paroisse (`paroisse=paroisse`) — c'est le lien **multi-tenant**.
5. **`groups.add(Group.objects.get(name="Curé"))`** : le premier compte reçoit
   le rôle Curé (accès complet). Les groupes de rôles sont créés en amont
   (migration/seed de `comptes`).
6. **`login(...)`** connecte immédiatement l'utilisateur, puis on redirige vers
   le tableau de bord. **Pas de paiement** : mode démonstration, l'offre est
   active tout de suite.

#### `TableauDeBordView` — accueil connecté avec compteurs

```python
class TableauDeBordView(LoginRequiredMixin, TemplateView):
    template_name = "core/tableau_de_bord.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser and request.user.paroisse is None:
            return redirect("plateforme:paroisse_liste")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        paroisse = self.request.user.paroisse
        context["paroisse"] = paroisse

        if paroisse is None:
            context["nombre_utilisateurs"] = 0
            context["nombre_paroissiens"] = 0
            context["nombre_actes_sacrements"] = 0
            context["nombre_dons"] = 0
            return context

        context["nombre_utilisateurs"] = Utilisateur.objects.filter(paroisse=paroisse).count()
        context["nombre_paroissiens"] = Paroissien.objects.filter(paroisse=paroisse).count()
        context["nombre_actes_sacrements"] = sum(
            modele.objects.filter(paroisse=paroisse).count()
            for modele in (Bapteme, Communion, Confirmation, Funerailles, Mariage)
        )
        context["nombre_dons"] = Don.objects.filter(paroisse=paroisse).count()
        return context
```

À défendre :

- **`LoginRequiredMixin`** : page réservée aux connectés. Un anonyme est redirigé
  vers la connexion (testé).
- **Aiguillage superadmin** : un superadmin **sans paroisse** (`paroisse is None`)
  n'a pas de tableau de bord paroissial ; il est renvoyé vers la console
  d'administration de la plateforme (`plateforme:paroisse_liste`).
- **Compteurs, tous filtrés `paroisse=paroisse`** : illustration directe de
  l'**isolation multi-tenant** — un utilisateur ne voit que les chiffres de
  **sa** paroisse.
- **Les actes sacramentels** additionnent 5 modèles (`Bapteme`, `Communion`,
  `Confirmation`, `Funerailles`, `Mariage`) via un `sum(... for modele in ...)`.
- **Garde `paroisse is None`** : compteurs à 0 plutôt qu'un plantage si le compte
  n'a pas de paroisse.

> Note MVT : la vue **ne calcule pas** quels compteurs afficher selon le rôle.
> C'est le template qui masque un compteur si le module est interdit
> (`{% if nav_finances %}`…), grâce aux variables `nav_*` / `est_cure` fournies
> par le **context processor** `navigation_par_role` de l'app `comptes`
> (enregistré dans `config/settings/base.py`). D'où le fait que le tableau de
> bord affiche des sections différentes pour un Curé et un Trésorier.

### [urls.py](../apps/core/urls.py) — le routage

```python
app_name = "core"

urlpatterns = [
    path("", AccueilView.as_view(), name="accueil"),
    path("fonctionnalites/", FonctionnalitesView.as_view(), name="fonctionnalites"),
    path("tarifs/", TarifsView.as_view(), name="tarifs"),
    path("souscription/", InscriptionView.as_view(), name="souscription"),
    path("tableau-de-bord/", TableauDeBordView.as_view(), name="tableau_de_bord"),
]
```

`app_name = "core"` → namespace : on référence toujours `core:accueil`,
`core:tableau_de_bord`, etc. `core` occupe la **racine `/`** du site (la vitrine
est la première chose qu'un visiteur voit).

### [admin.py](../apps/core/admin.py) — l'admin singleton

```python
@admin.register(ContenuVitrine)
class ContenuVitrineAdmin(admin.ModelAdmin):
    list_display = ("__str__", "titre_hero")

    def has_add_permission(self, request):
        # Singleton : une seule ligne, créée à la demande par charger().
        return not ContenuVitrine.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
```

Renforce le patron singleton **côté interface** : on ne peut **ajouter** une
ligne que s'il n'en existe aucune, et on ne peut **jamais supprimer** la ligne
existante. L'admin ne sert donc qu'à **éditer** le contenu du hero.

### [apps.py](../apps/core/apps.py) — configuration de l'app

`label = "core"`, `verbose_name = "Vitrine et tableau de bord"`,
`default_auto_field = BigAutoField`. Rien de spécial, mais le `verbose_name`
résume bien la double casquette de l'app.

---

## Templates de `templates/core/`

Tous les templates **étendent une base** (`base_public.html` pour la vitrine,
`base_app.html` pour l'espace connecté) et utilisent la grille Bootstrap
surchargée par le thème custom (classes `carte`, `bouton-principal`,
`suscription`, `numerique`…). Séparation Vue/Contrôleur respectée.

- **[accueil.html](../apps/core/templates/core/accueil.html)** — page d'accueil
  vitrine. Affiche le hero éditable (`{{ contenu.titre_hero }}`,
  `accroche_hero`, image optionnelle), le bandeau liturgique « Temps ordinaire »,
  trois cartes de présentation (paroissiens, sacrements, célébrations/dons), et
  un bloc CTA final (`{{ contenu.titre_cta }}`) menant à `core:souscription`.

- **[fonctionnalites.html](../apps/core/templates/core/fonctionnalites.html)** —
  page « Cinq modules, un seul registre » : six cartes détaillant paroissiens,
  sacrements, célébrations, dons/reçus, communication, localisation. Contenu
  statique, purement descriptif.

- **[tarifs.html](../apps/core/templates/core/tarifs.html)** — grille des offres.
  Boucle `{% for valeur, libelle, limites in offres %}` sur le contexte fourni
  par `TarifsView`. Affiche `limites.prix_affiche`, la liste des modules inclus
  (conditionnée par `{% if "paroissiens" in limites.modules %}` etc.), les
  plafonds d'utilisateurs/paroissiens, met « Standard » en avant
  (`carte-tarif--mise-en-avant`), et chaque bouton pointe vers
  `core:souscription?offre={{ valeur }}` (d'où la pré-sélection).

- **[souscription.html](../apps/core/templates/core/souscription.html)** —
  formulaire d'inscription + **carte Leaflet interactive**. Deux sections
  (« Votre paroisse », « Votre compte administrateur ») rendues via le partial
  `partials/_form_field.html`. Un bandeau « Mode démonstration » prévient qu'il
  n'y a pas de paiement. Le JavaScript :
  - initialise une carte Leaflet (centrée sur Kinshasa par défaut) ;
  - bouton « Rechercher sur la carte » → `fetch("/api/rechercher-adresse/")`
    (géocodage Nominatim direct) puis liste de résultats cliquables ;
  - **clic sur la carte** → `fetch("/api/geocoder-inverse/")` qui **remplit
    automatiquement** avenue/quartier/commune/ville depuis les coordonnées ;
  - **arrondit lat/lng à 6 décimales** avant de remplir les champs cachés —
    commentaire explicite dans le code : sans cet arrondi la validation du
    `DecimalField(decimal_places=6)` échouerait silencieusement (champs cachés,
    aucune erreur visible) et rien ne serait enregistré.

- **[tableau_de_bord.html](../apps/core/templates/core/tableau_de_bord.html)** —
  accueil connecté. Affiche jusqu'à quatre `compteurs` (utilisateurs,
  paroissiens, actes, dons) — chacun conditionné par les droits (`nav_*`), avec
  chiffres tabulaires (`numerique`). Bloc « Localisation » : si la paroisse a des
  coordonnées, une **carte Leaflet** (`id="carte-paroisse"`) affiche un marqueur ;
  sinon, un avis « Localisation non renseignée » et, **pour le Curé seulement**
  (`{% if est_cure %}`), un bouton « Localiser automatiquement » qui appelle
  `POST /api/paroisse/geocoder/` (géocodage Nominatim de l'adresse) puis recharge
  la page.

---

## Tests

### [test_pages_publiques.py](../apps/core/tests/test_pages_publiques.py)

- `test_page_publique_accessible` (paramétré sur accueil, fonctionnalités,
  tarifs, souscription) : chaque page publique répond **200** sans connexion.
- `test_souscription_preselectionne_offre_depuis_la_query_string` : `GET
  /souscription/?offre=standard` renvoie du HTML contenant
  `value="standard" selected` → la pré-sélection via `get_initial()` marche.
- `test_tableau_de_bord_exige_authentification` : un anonyme est **redirigé
  (302)** vers `comptes:connexion` → `LoginRequiredMixin` actif.

### [test_inscription.py](../apps/core/tests/test_inscription.py)

Utilise l'usine `_donnees_valides(**overrides)` (jeu de données Saint Raphaël).

- `test_inscription_cree_paroisse_abonnement_et_compte_cure` : le POST crée bien
  la **paroisse** (avec `adresse` composée `"12 avenue de la Cathédrale, Golf,
  Gombe"`), l'**abonnement** (offre standard, statut `actif`), le **Curé**
  (rattaché à la paroisse, dans le groupe Curé, mot de passe **haché** vérifié
  par `check_password`), et redirige (302) vers le tableau de bord. Coordonnées
  `None` quand non fournies.
- `test_inscription_connecte_automatiquement_le_nouvel_utilisateur` : après le
  POST, un `GET` du tableau de bord répond **200** (l'utilisateur est déjà
  connecté) et affiche « Saint Raphaël ».
- `test_inscription_refuse_un_nom_de_paroisse_deja_pris` : renvoie 200 avec
  « porte déjà ce nom » → `clean_nom_paroisse`.
- `test_inscription_refuse_un_nom_d_utilisateur_deja_pris` : renvoie 200 avec
  « déjà pris », **et** aucune paroisse Saint Raphaël n'a été créée → preuve du
  **rollback** transactionnel (la paroisse n'est pas orpheline).
- `test_inscription_refuse_des_mots_de_passe_differents` : « ne correspondent
  pas », rien créé.
- `test_inscription_refuse_un_mot_de_passe_trop_simple` (`12345678`) : rejeté par
  `validate_password`, rien créé.
- `test_inscription_enregistre_les_coordonnees_pointees_sur_la_carte` : lat/lng
  fournies sont bien persistées telles quelles.
- `test_inscription_sans_quartier_compose_l_adresse_sans_lui` : sans quartier,
  `adresse == "12 avenue de la Cathédrale, Gombe"` (pas de virgule vide).

### [test_tableau_de_bord.py](../apps/core/tests/test_tableau_de_bord.py)

- `test_tableau_de_bord_affiche_le_nombre_d_utilisateurs` : 2 utilisateurs créés
  → la page affiche « Saint Raphaël » et le compteur `>2<`.
- `test_tableau_de_bord_sans_localisation_affiche_un_avis` : sans coordonnées,
  message « Localisation non renseignée » et **pas** de `id="carte-paroisse"`.
- `test_tableau_de_bord_avec_localisation_affiche_la_carte` : avec lat/lng, la
  div `id="carte-paroisse"` est présente (Leaflet sera monté).
- `test_navigation_du_cure_affiche_toutes_les_sections` : un Curé voit
  Paroissiens, Sacrements, Célébrations, Finances, Communication.
- `test_navigation_du_tresorier_limitee_aux_finances` : un Trésorier voit
  « Finances » mais **pas** Paroissiens ni Sacrements → **permissions par rôle**
  appliquées à la navigation.

---

## Questions probables du jury & réponses

**Q1. Pourquoi `devises.py` est-il dans `core` et pas dans `finances` ?**
Parce que `finances` **et** `celebrations` en ont besoin. Le placer dans l'une
forcerait l'autre à en dépendre → dépendance croisée entre apps métier. `core`
est une app feuille (sans dépendance métier), donc les deux peuvent y importer
les devises sans créer de cycle. C'est le principe de la dépendance stable.

**Q2. Que se passe-t-il si la création du Curé échoue en plein milieu de
l'inscription ?** Tout est annulé. Les trois créations sont dans un même
`transaction.atomic()` : au moindre échec, rollback complet, aucune paroisse ni
abonnement orphelin. Le test `..._refuse_un_nom_d_utilisateur_deja_pris` le
prouve (la paroisse n'existe pas après l'erreur).

**Q3. Pourquoi un `forms.Form` et pas un `ModelForm` ?** Parce que le formulaire
crée **plusieurs** objets (Paroisse, Abonnement, Utilisateur) et compose
l'adresse à partir de plusieurs champs. Un `ModelForm` est lié à un seul modèle ;
ici la logique de création multi-objets vit dans `form_valid`.

**Q4. Comment garantissez-vous qu'il n'y a qu'un seul `ContenuVitrine` ?** Deux
verrous. Côté code : `charger()` fait `get_or_create(pk=1)`, on ne manipule
jamais qu'une ligne. Côté admin : `has_add_permission` interdit d'ajouter s'il en
existe déjà une, `has_delete_permission` renvoie toujours `False`.

**Q5. Le tableau de bord illustre-t-il le multi-tenant ?** Oui : chaque compteur
est un `.filter(paroisse=paroisse).count()` sur la paroisse de l'utilisateur
connecté. Personne ne voit les chiffres d'une autre paroisse. Le superadmin sans
paroisse est même redirigé vers la console plateforme.

**Q6. Où est la consommation de l'API externe Nominatim (critère 8b) ?** Côté
`core`, dans les templates : `souscription.html` appelle
`/api/rechercher-adresse/` (géocodage direct) et `/api/geocoder-inverse/`
(remplit l'adresse depuis un clic), `tableau_de_bord.html` appelle
`/api/paroisse/geocoder/`. Le résultat est affiché sur une carte **Leaflet**.
Les endpoints qui contactent réellement Nominatim sont définis côté API/comptes ;
`core` fournit l'interface utilisateur.

**Q7. Comment le tableau de bord adapte-t-il son affichage au rôle ?** La vue
fournit tous les compteurs ; c'est le template qui masque un bloc selon les
variables `nav_paroissiens`, `nav_sacrements`, `nav_finances`, `est_cure`. Elles
proviennent du context processor `navigation_par_role` de l'app `comptes`
(enregistré dans `config/settings/base.py`), qui calcule les droits d'après les
groupes de l'utilisateur. Testé pour le Curé et le Trésorier.

**Q8. Pourquoi arrondir les coordonnées à 6 décimales dans le JavaScript ?**
Parce que `Paroisse.latitude`/`longitude` sont des `DecimalField(max_digits=9,
decimal_places=6)`. Nominatim et un clic sur la carte renvoient bien plus de
décimales ; sans arrondi, le `DecimalField` (champ caché) rejetterait la valeur
et le formulaire échouerait **silencieusement**, sans rien enregistrer.

**Q9. L'inscription implique-t-elle un paiement ?** Non, c'est un mode
démonstration assumé (bandeau « Mode démonstration » sur la page). L'offre
choisie est activée immédiatement (`Abonnement` créé avec statut actif), l'idée
étant de montrer le parcours complet sans passerelle de paiement pour la
soutenance.

**Q10. Comment le premier utilisateur devient-il Curé ?** À la fin de la
transaction d'inscription :
`cure.groups.add(Group.objects.get(name="Curé"))`. Le compte créé lors de la
souscription reçoit d'office le rôle Curé (accès complet à la paroisse). Les
autres membres seront ensuite invités par ce Curé (fonctionnalité de l'app
`comptes`).
