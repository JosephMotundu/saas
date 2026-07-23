# App `comptes` — utilisateurs, sécurité et cœur du multi-tenant

> Fiche de révision pour la soutenance. Tout ce qui est décrit ici renvoie au
> vrai code, avec des liens cliquables. À lire avant de défendre l'architecture
> de sécurité et d'isolation des données du projet.

## Rôle de l'app dans le projet

`comptes` est l'app **fondation** de ParoisseConnect. Elle porte trois
responsabilités qui conditionnent toutes les autres apps :

1. **Les deux modèles pivots** : `Paroisse` (le *tenant*, c'est-à-dire le client
   qui loue l'instance) et `Utilisateur` (le modèle d'utilisateur custom, rattaché
   à une paroisse). Chaque entité métier du projet (`Paroissien`, `Bapteme`,
   `Don`, `Annonce`…) porte une clé étrangère vers `Paroisse` — cette FK est
   définie ici.
2. **La mécanique multi-tenant** : la ContextVar, le middleware, le manager
   automatique et les mixins de vue qui garantissent qu'une paroisse ne peut
   jamais voir les données d'une autre. C'est la pièce technique la plus
   défendable du projet.
3. **La sécurité et les rôles** : authentification, connexion/déconnexion,
   gestion de l'équipe par le Curé (invitations, rôles, mots de passe), profil,
   et l'abonnement SaaS (offre et modules autorisés).

Le fichier de référence sur les besoins est [CLAUDE.md](../CLAUDE.md) (le brief
et la liste des 16 critères du jury).

---

## Critères du jury démontrés ici

| Critère (§3 du brief) | Où le montrer dans `comptes` |
|---|---|
| **1. BDD relationnelle** (1:1, 1:N, contraintes) | [models.py](../apps/comptes/models.py) : `Utilisateur` → `Paroisse` en 1:N (`ForeignKey`), `Abonnement` → `Paroisse` en 1:1 (`OneToOneField`), contraintes `unique=True` sur `nom`/`slug`, `null`/`blank` maîtrisés. |
| **2. Langage backend** | Python 3.12 / Django 5, tout le dossier. |
| **3. Authentification** (mots de passe hachés) | [test_models.py](../apps/comptes/tests/test_models.py) prouve `check_password()` et `password != mot_de_passe`. 2FA TOTP et JWT sont configurés au niveau projet (voir §Note ci-dessous). |
| **6. Architecture MVT** | Séparation stricte : Model = [models.py](../apps/comptes/models.py), View (contrôleur) = [views.py](../apps/comptes/views.py), Template = dossier `templates/comptes/`, logique réutilisable dans [mixins.py](../apps/comptes/mixins.py) et [managers.py](../apps/comptes/managers.py). |
| **7. Rôles et permissions** | Groupes Django créés par la migration [0002](../apps/comptes/migrations/0002_creer_groupes_roles.py) ; `RoleRequisMixin` dans [mixins.py](../apps/comptes/mixins.py) protège les vues. |
| **9. POO** | Méthodes métier sur les modèles (`Abonnement.annuler()`, `module_autorise()`…), fabrique de manager (`creer_manager_paroisse()`), mixins réutilisables. |
| **11. Tests unitaires** | 13 fichiers dans [tests/](../apps/comptes/tests/) : modèles, isolation, middleware, permissions, limites d'offre… |
| **13. Automatisation** | Commande [seed.py](../apps/comptes/management/commands/seed.py) idempotente. |
| **14. Transactions** | `@transaction.atomic` sur `seed.handle()`. |
| **15. Backoffice admin** | [admin.py](../apps/comptes/admin.py) : `list_display`, `list_filter`, `search_fields`, isolation par paroisse. |
| **Multi-tenant (§4)** | ContextVar + middleware + manager + mixins : le cœur de cette app. |

> **Note sur la 2FA et le JWT** : ces deux mécanismes (`django_otp`,
> `rest_framework_simplejwt`) sont branchés au niveau du projet dans
> [config/settings/base.py](../config/settings/base.py) (voir `INSTALLED_APPS`,
> `MIDDLEWARE` avec `OTPMiddleware`, et le bloc `SIMPLE_JWT`), pas dans l'app
> `comptes` elle-même. L'app `comptes` fournit le **hachage des mots de passe**
> (hérité d'`AbstractUser`) ; la 2FA et le JWT sont documentés dans l'app `api`
> et dans [config/settings/SETTINGS.md](../config/settings/SETTINGS.md).

---

## Fichier par fichier

### [models.py](../apps/comptes/models.py) — les trois modèles

#### `Paroisse` — le tenant

C'est **l'entité qui isole les données**. Chaque autre modèle du projet pointe
vers elle. Points à défendre :

- `nom = CharField(unique=True)` : contrainte d'unicité (critère BDD).
- `slug = SlugField(unique=True, blank=True)` : identifiant public utilisé dans
  l'URL de la page publique de la paroisse. Il est **généré automatiquement**
  dans `save()` :

  ```python
  def save(self, *args, **kwargs):
      if not self.slug:
          base = slugify(self.nom) or "paroisse"
          slug = base
          compteur = 1
          while Paroisse.objects.filter(slug=slug).exclude(pk=self.pk).exists():
              compteur += 1
              slug = f"{base}-{compteur}"
          self.slug = slug
      super().save(*args, **kwargs)
  ```

  La boucle garantit l'unicité même si deux paroisses ont un nom qui produit le
  même slug (« saint-raphael », « saint-raphael-2 »…).
- `latitude` / `longitude` en `DecimalField(null=True, blank=True)` : remplies
  par le géocodage Nominatim (critère 8, API externe).
- `est_active = BooleanField(default=True)` : **suspension par la plateforme**
  (distincte de l'abonnement que le Curé gère lui-même). Décoché, plus personne
  ne peut se connecter — c'est ce que vérifient le middleware et le
  `ConnexionForm`.
- `commune`, `quartier`, `avenue` : l'adresse complète est composée à partir de
  ces champs à l'inscription.

#### `Abonnement` — la facturation SaaS (1:1)

À ne pas confondre avec les `Don`/`RecuFiscal` de l'app `finances` (qui sont la
comptabilité *interne* de la paroisse). `Abonnement` est la facturation de
l'instance ParoisseConnect elle-même.

- **Relation 1:1** : `paroisse = OneToOneField(Paroisse, related_name="abonnement")`.
  Une paroisse a exactement un abonnement.
- Le dictionnaire de classe `LIMITES` est la **source unique de vérité** partagée
  entre l'affichage (page tarifs) et le **contrôle d'accès réel** :

  ```python
  LIMITES = {
      "essentiel": {"prix_affiche": "15 $ / mois", "max_utilisateurs_supplementaires": 3,
                    "max_paroissiens": None, "modules": frozenset({"sacrements", "celebrations", "finances"})},
      "standard":  {..., "max_utilisateurs_supplementaires": 7, "max_paroissiens": 2000,
                    "modules": frozenset({..., "paroissiens"})},
      "pro":       {..., "max_utilisateurs_supplementaires": None, "max_paroissiens": None,
                    "modules": frozenset({..., "paroissiens", "communication"})},
  }
  ```

  `None` signifie « illimité ». À défendre : *les tarifs ne sont pas que du texte
  marketing, ils sont appliqués par du code* (voir `ModuleAutoriseMixin` et la
  vue d'invitation).
- **Méthodes métier (POO)** : `annuler()` et `reactiver()` changent le statut et
  la date d'annulation via `save(update_fields=...)` ; `limites()`,
  `module_autorise(nom)`, `max_utilisateurs_supplementaires()`,
  `max_paroissiens()`, `prix_affiche()` lisent la config de l'offre courante.

#### `Utilisateur(AbstractUser)` — le modèle d'utilisateur custom

- Hérite d'`AbstractUser` : on récupère username, mot de passe **haché**,
  groupes, permissions, `is_active`, `is_superuser`… sans réécrire l'auth.
- **Le seul champ ajouté** est la FK vers la paroisse :

  ```python
  paroisse = models.ForeignKey(
      Paroisse, related_name="utilisateurs",
      on_delete=models.PROTECT, null=True, blank=True,
      help_text="Laisser vide pour un compte d'administration d'instance (superadmin).")
  ```

  - `on_delete=PROTECT` : on ne peut pas supprimer une paroisse s'il reste des
    utilisateurs rattachés (intégrité référentielle).
  - `null=True` : le **superadmin d'instance** (paroisse=None) administre
    *plusieurs* paroisses ; il n'est rattaché à aucune. C'est la seule exception
    à la règle « tout utilisateur a une paroisse ».
- `__str__` renvoie le nom complet ou le username.
- Ce modèle est déclaré comme `AUTH_USER_MODEL` dans les settings (sinon Django
  utiliserait son `User` par défaut).

---

### [managers.py](../apps/comptes/managers.py) — le manager multi-tenant automatique

**La pièce maîtresse de l'isolation.** `creer_manager_paroisse()` est une
**fabrique** (factory function) qui retourne un manager dont le `get_queryset()`
filtre automatiquement sur la paroisse courante :

```python
def creer_manager_paroisse(champ_paroisse="paroisse"):
    class ParoisseQuerySet(models.QuerySet):
        def de_la_paroisse_courante(self):
            paroisse = obtenir_paroisse_courante()
            if paroisse is None:
                return self
            return self.filter(**{champ_paroisse: paroisse})

    class ParoisseManager(models.Manager.from_queryset(ParoisseQuerySet)):
        def get_queryset(self):
            return super().get_queryset().de_la_paroisse_courante()

    return ParoisseManager()
```

Points à défendre :

- Les modèles métier des autres apps déclarent `objects = creer_manager_paroisse()`.
  Dès lors, **toute requête** `Paroissien.objects.all()` est déjà filtrée sur la
  paroisse courante, sans que le développeur ait à y penser.
- Le paramètre `champ_paroisse` permet de filtrer via une **relation indirecte** :
  un modèle sans FK `paroisse` directe (ex. `RecuFiscal`) passe
  `creer_manager_paroisse("don__paroisse")`. C'est testé dans
  [test_managers.py](../apps/comptes/tests/test_managers.py).
- **Comportement hors requête** : si aucune paroisse n'est définie dans la
  ContextVar (migrations, shell, commande `seed`, tests directs), `paroisse is
  None` → aucun filtrage. On ne veut pas casser ces usages légitimes. Un
  superadmin (paroisse=None) n'est jamais filtré non plus, par conception.
- Le commentaire du fichier insiste : ce manager est une **défense en profondeur**,
  pas le seul rempart. Les vues filtrent *aussi* explicitement (voir
  `FiltrageParoisseMixin`). Deux barrières indépendantes valent mieux qu'une.
- Bénéfice caché : comme le Django Admin utilise `ModelAdmin.get_queryset()` qui
  s'appuie sur le manager par défaut, l'admin hérite gratuitement de l'isolation.

---

### [contexte.py](../apps/comptes/contexte.py) — la paroisse courante (ContextVar)

Le « lieu » où est stockée la paroisse de la requête en cours, pour que le
manager (qui n'a pas accès à `request`) puisse la lire.

```python
_paroisse_courante: ContextVar = ContextVar("paroisse_courante", default=None)

def definir_paroisse_courante(paroisse):   return _paroisse_courante.set(paroisse)
def obtenir_paroisse_courante():           return _paroisse_courante.get()
def reinitialiser_paroisse_courante(jeton): _paroisse_courante.reset(jeton)
```

À défendre :

- **Pourquoi une `ContextVar` et pas un `threading.local` ?** La `ContextVar`
  reste correcte sous un serveur **ASGI/async** : chaque contexte async a sa
  propre valeur, alors qu'un `threading.local` fuiterait entre coroutines
  partageant un thread. C'est un choix d'architecture défendable et moderne.
- `set()` renvoie un **jeton** (token) qui sert à `reset()` pour restaurer la
  valeur précédente proprement — indispensable pour ne pas laisser fuiter une
  paroisse d'une requête sur la suivante.

---

### [middleware.py](../apps/comptes/middleware.py) — pose la paroisse courante

`ParoisseCouranteMiddleware` fait le lien entre l'utilisateur connecté et la
ContextVar. Il s'exécute à **chaque requête** :

```python
def __call__(self, request):
    utilisateur = getattr(request, "user", None)
    paroisse = None
    if utilisateur is not None and utilisateur.is_authenticated:
        paroisse = getattr(utilisateur, "paroisse", None)
        if paroisse is not None and not paroisse.est_active:
            # paroisse suspendue en cours de session -> on coupe l'accès
            ...
            logout(request)
            return redirect("comptes:connexion")
    request.paroisse = paroisse
    jeton = definir_paroisse_courante(paroisse)
    try:
        response = self.get_response(request)
    finally:
        reinitialiser_paroisse_courante(jeton)
    return response
```

Trois choses à retenir :

1. **Il expose `request.paroisse`** (pratique pour les vues) ET **alimente la
   ContextVar** (pour les managers). Un seul point de vérité, deux consommateurs.
2. **Suspension à chaud** : si la plateforme suspend une paroisse pendant qu'un
   utilisateur est déjà connecté, le middleware le **déconnecte immédiatement**
   (sauf sur les pages de connexion/déconnexion, pour éviter une boucle). Sans
   ça, la suspension n'aurait d'effet qu'à la prochaine reconnexion.
3. **Nettoyage garanti** : le `reset()` est dans un `finally`, donc la ContextVar
   est réinitialisée même si la vue lève une exception. Prouvé par
   `test_contextvar_reinitialisee_apres_la_requete`.

**Ordre dans `MIDDLEWARE`** : placé *après* `AuthenticationMiddleware` (il a
besoin de `request.user`). Vérifiable dans
[config/settings/base.py](../config/settings/base.py).

---

### [mixins.py](../apps/comptes/mixins.py) — les gardes de vue réutilisables (POO)

Quatre mixins qui s'assemblent par héritage multiple sur les vues.

- **`FiltrageParoisseMixin(LoginRequiredMixin)`** — isolation au niveau vue :
  ```python
  def get_queryset(self):
      return super().get_queryset().filter(paroisse=self.request.paroisse)
  def form_valid(self, form):
      form.instance.paroisse = self.request.paroisse
      return super().form_valid(form)
  ```
  Filtre explicitement (redondant avec le manager = défense en profondeur) ET
  rattache automatiquement tout objet créé à la paroisse courante.

- **`RoleRequisMixin(LoginRequiredMixin, UserPassesTestMixin)`** — contrôle de
  rôle :
  ```python
  roles_autorises = ()
  def test_func(self):
      utilisateur = self.request.user
      if utilisateur.is_superuser:
          return True
      groupes = set(utilisateur.groups.values_list("name", flat=True))
      if "Curé" in groupes:
          return True
      return bool(groupes & set(self.roles_autorises))
  ```
  Le **Curé et le superadmin ont toujours accès** (§7 : « Curé : accès complet »).
  Les autres passent si l'un de leurs groupes est dans `roles_autorises`. Un
  échec renvoie **403** (comportement d'`UserPassesTestMixin`), pas une
  redirection — visible dans les tests.

- **`ExigeParoisseMixin`** — empêche un superadmin (paroisse=None) d'atteindre
  une vue qui *suppose* une paroisse (abonnement, équipe). Redirige vers le
  tableau de bord avec un message. Prouvé par
  `test_superadmin_sans_paroisse_redirige_proprement`.

- **`ModuleAutoriseMixin`** — bloque une vue si le module n'est pas dans l'offre :
  ```python
  module_requis = None
  def dispatch(self, request, *args, **kwargs):
      if not request.user.is_superuser and request.paroisse is not None:
          abonnement = getattr(request.paroisse, "abonnement", None)
          if abonnement is not None and not abonnement.module_autorise(self.module_requis):
              messages.error(...); return redirect("core:tableau_de_bord")
      return super().dispatch(request, *args, **kwargs)
  ```
  Utilisé par les vues des apps `paroissiens` et `communication`. Si la paroisse
  n'a **pas** d'abonnement, l'accès reste ouvert : la limite est une règle de
  *facturation*, pas de *sécurité* — elle ne doit jamais casser un usage interne
  de confiance faute de config. Prouvé par `test_module_non_restreint_sans_abonnement`.

---

### [context_processors.py](../apps/comptes/context_processors.py) — la navigation par rôle

`navigation_par_role(request)` est un **context processor** : il injecte des
booléens dans *tous* les templates, pour afficher ou masquer chaque entrée du
menu selon **deux critères combinés** — le rôle ET le module inclus dans l'offre.

```python
role_paroissiens = est_cure or est_lecteur or "Secrétaire" in groupes
return {
    "nav_paroissiens": role_paroissiens and module_autorise("paroissiens"),
    "nav_sacrements":  est_cure or est_lecteur or "Secrétaire" in groupes,
    "nav_celebrations": est_cure or est_lecteur or "Secrétaire" in groupes,
    "nav_finances":    est_cure or est_lecteur or "Trésorier" in groupes,
    "nav_communication": role_communication and module_autorise("communication"),
    "est_cure": est_cure,
}
```

À défendre :

- **Un Curé ne voit pas un module que son offre n'inclut pas** : le rôle ne
  suffit pas, le module doit aussi être autorisé. Cohérent avec
  `ModuleAutoriseMixin`.
- C'est de l'**affichage** seulement. La vraie sécurité est côté vue (les mixins).
  Masquer un lien n'empêche pas d'atteindre l'URL — c'est pourquoi les deux
  couches coexistent. Prouvé par `test_navigation_masque_les_modules_non_inclus`.

---

### [forms.py](../apps/comptes/forms.py) — formulaires et validation

- **`ConnexionForm(AuthenticationForm)`** : personnalise les widgets (classes
  CSS du thème, placeholders, autofocus) et surtout **surcharge
  `confirm_login_allowed()`** pour refuser la connexion si la paroisse est
  suspendue :
  ```python
  def confirm_login_allowed(self, user):
      super().confirm_login_allowed(user)
      if user.paroisse is not None and not user.paroisse.est_active:
          raise forms.ValidationError("Votre paroisse a été suspendue. ...",
                                      code="paroisse_suspendue")
  ```
  C'est la barrière *à la connexion* ; le middleware est la barrière *en cours de
  session*. Les deux ensemble = suspension étanche.
- **`ProfilForm(ModelForm)`** : édition de `first_name`, `last_name`, `email`.
- **`InvitationForm(Form)`** : le Curé invite un collaborateur (prénom, nom,
  email, nom d'utilisateur, rôle). `clean_nom_utilisateur()` rejette un username
  déjà pris (insensible à la casse, `username__iexact`) ; `clean_role()` vérifie
  que le groupe existe. Le mot de passe n'est **pas** dans le formulaire : il est
  généré côté serveur (voir la vue).
- **`MembreModifierForm(Form)`** : modifie coordonnées + rôle d'un membre. Le
  username n'est volontairement pas modifiable (identifiant stable).
- **`ChangerOffreForm(Form)`** : un seul champ `offre`, alimenté par
  `Abonnement.OFFRE_CHOICES`.

---

### [views.py](../apps/comptes/views.py) — les contrôleurs (couche V du MVT)

Mélange de vues génériques Django et de vues `View` explicites. Toutes les vues
sensibles combinent les mixins d'isolation/rôle.

- **`ConnexionView(LoginView)`** : utilise `ConnexionForm`,
  `redirect_authenticated_user=True`.
- **`ProfilView` / `ProfilModifierView`** : « Mon compte ». `ProfilModifierView`
  surcharge `get_object()` pour retourner `self.request.user` (on ne modifie que
  soi-même).
- **`EquipeListView(FiltrageParoisseMixin, ListView)`** : liste les membres de la
  paroisse. Optimisation requête (critère 14) :
  `super().get_queryset().prefetch_related("groups")` évite le N+1 sur les rôles.
- **`InvitationCreateView(RoleRequisMixin, ExigeParoisseMixin, View)`** — création
  d'un compte collègue. Deux points forts à défendre :
  1. **Contrôle de la limite d'utilisateurs de l'offre** avant création :
     ```python
     compte_actuel = (Utilisateur.objects.filter(paroisse=request.paroisse)
                      .exclude(groups__name="Curé").count())
     if compte_actuel >= limite: messages.error(...); return redirect("comptes:equipe")
     ```
     Les Curés ne comptent pas dans la limite (`exclude(groups__name="Curé")`).
  2. **Mot de passe temporaire généré côté serveur** avec `secrets.token_urlsafe(9)`
     (cryptographiquement sûr), jamais choisi par l'inviteur, affiché une seule
     fois. Création via `Utilisateur.objects.create_user(...)` (donc mot de passe
     haché) puis `membre.groups.add(Group.objects.get(name=...))`.
- **`MembreBasculerActifView`** : active/désactive un membre. Refuse de se
  désactiver soi-même (`if membre == request.user`).
- **`MembreModifierView`** : modifie coordonnées + rôle. Refuse de se modifier
  soi-même via cette page (renvoie vers « Mon compte »). `membre.groups.set([...])`
  remplace le rôle. `get_object_or_404(..., paroisse=request.paroisse)` garantit
  qu'on ne touche pas un membre d'une autre paroisse (renvoie 404).
- **`MembreReinitialiserMotDePasseView`** : régénère un mot de passe temporaire
  pour un membre (le Curé n'a pas besoin du superadmin pour ça).
- **`AbonnementView` / `AbonnementBasculerStatutView`** : le Curé consulte les
  offres, change d'offre (`ChangerOffreForm`), annule/réactive l'abonnement
  (appelle `abonnement.annuler()` / `.reactiver()`).

Toutes ces vues d'équipe/abonnement héritent de
`RoleRequisMixin, ExigeParoisseMixin` : réservées au Curé, et interdites au
superadmin sans paroisse.

---

### [admin.py](../apps/comptes/admin.py) — backoffice (critère 15)

Trois `ModelAdmin` enregistrés, tous avec `list_display`, `list_filter`,
`search_fields` (exigence du jury).

Point crucial : **`Paroisse` et `Utilisateur` ne portent pas le manager
multi-tenant automatique** — `Paroisse` *est* le tenant, et `Utilisateur` est lu
pendant l'authentification, *avant* qu'une paroisse courante soit connue.
L'isolation est donc rétablie **explicitement dans l'admin** :

```python
def get_queryset(self, request):
    queryset = super().get_queryset(request)
    if request.user.is_superuser:
        return queryset
    return queryset.filter(pk=request.user.paroisse_id)   # ParoisseAdmin
    # ... .filter(paroisse=request.user.paroisse)          # Utilisateur/Abonnement Admin
```

`UtilisateurAdmin` étend le `UserAdmin` de Django et ajoute la paroisse aux
`fieldsets`, `add_fieldsets`, `list_display`, `list_filter`. Le superadmin voit
tout ; un Curé ne voit que sa paroisse. Prouvé par
[test_admin_isolation.py](../apps/comptes/tests/test_admin_isolation.py).

---

### [urls.py](../apps/comptes/urls.py) — routage

`app_name = "comptes"` (namespace). Routes : `connexion`, `deconnexion`
(`LogoutView`), `profil`, `profil_modifier`, changement de mot de passe
(`PasswordChangeView` / `PasswordChangeDoneView` de Django, avec templates
custom), et le bloc « équipe » (`equipe`, `equipe_inviter`,
`equipe_basculer_actif`, `equipe_modifier`, `equipe_reinitialiser_mot_de_passe`)
+ `abonnement` / `abonnement_basculer_statut`.

### [apps.py](../apps/comptes/apps.py)

`ComptesConfig` : `name = "apps.comptes"`, `label = "comptes"` (le label court
sert de préfixe aux migrations et aux tables).

---

### [management/commands/seed.py](../apps/comptes/management/commands/seed.py) — données de démo (critères 13 et 14)

Commande `python manage.py seed`. À défendre :

- **`@transaction.atomic` sur `handle()`** : tout ou rien. Si une étape échoue,
  rien n'est écrit (critère 14, transactions).
- **Idempotente** : elle utilise `update_or_create` / `get_or_create` partout et
  des identifiants stables (dictionnaire `COMPTES_DEMO`). La relancer ne crée pas
  de doublons — prouvé par `test_seed_est_idempotent`.
- Crée la **paroisse Saint Raphaël** (Kinshasa, coordonnées géographiques
  incluses), son **abonnement** (offre `standard`), **5 comptes** : un superadmin
  (`admin`, sans paroisse) + un par rôle (`cure`, `secretaire`, `tresorier`,
  `lecteur`), chacun rattaché à son groupe via `groups.set([...])`.
- Puis un jeu de démo réaliste couvrant les autres apps : famille, paroissien,
  baptême, célébration + intention de messe, dons en deux devises (via le service
  `enregistrer_don_avec_recu`), offrande de messe, dépenses, annonce. Utile pour
  démontrer l'app entière en soutenance sans saisie manuelle.
- À la fin, elle **affiche les identifiants** de connexion dans la console.

---

## Les tests — ce qu'ils prouvent au jury

Tous sous `pytest.mark.django_db`. Lancer : `pytest apps/comptes/`.

| Fichier | Ce qu'il vérifie / pourquoi c'est important |
|---|---|
| [test_models.py](../apps/comptes/tests/test_models.py) | Création de `Paroisse` et `Utilisateur`, rattachement à une paroisse, superadmin sans paroisse. **Prouve le hachage** : `check_password()` OK et `password != mot_de_passe` (critère 3). |
| [test_managers.py](../apps/comptes/tests/test_managers.py) | Le manager **filtre** quand la paroisse courante est définie, **ne filtre pas** hors contexte, et filtre via **relation indirecte** (`RecuFiscal` → `don__paroisse`). Cœur de l'isolation. |
| [test_middleware.py](../apps/comptes/tests/test_middleware.py) | Le middleware expose la bonne paroisse pour un utilisateur connecté, `None` pour superadmin et anonyme, et **réinitialise la ContextVar après la requête** (pas de fuite entre requêtes). |
| [test_admin_isolation.py](../apps/comptes/tests/test_admin_isolation.py) | L'admin isole les non-superusers (Paroisse et Utilisateur via `get_queryset` explicite ; Paroissien via le manager + ContextVar). Superadmin voit tout. Critère 15 + §4. |
| [test_groupes.py](../apps/comptes/tests/test_groupes.py) | Les 4 groupes de rôles existent (créés par la migration) et **seuls** ces 4-là existent. Critère 7. |
| [test_vues_auth.py](../apps/comptes/tests/test_vues_auth.py) | Page de connexion accessible, connexion avec identifiants valides (302), déconnexion. Critère 3. |
| [test_profil.py](../apps/comptes/tests/test_profil.py) | Affichage du profil, mise à jour des champs, **changement de mot de passe** (re-vérifié via `check_password`), et le profil **exige l'authentification** (redirection sinon). |
| [test_suspension.py](../apps/comptes/tests/test_suspension.py) | Connexion refusée si paroisse suspendue, connexion normale sinon, **session coupée à chaud** dès la suspension, accès restauré à la réactivation. Prouve les deux barrières (form + middleware). |
| [test_equipe.py](../apps/comptes/tests/test_equipe.py) | Le Curé invite (le mot de passe temporaire affiché **permet réellement de se connecter**), un Secrétaire **ne peut pas** inviter (403), équipe **isolée par paroisse**, désactivation, modification de rôle, réinitialisation de mot de passe, impossibilité de se désactiver/modifier soi-même, 404 sur un membre d'une autre paroisse. Couverture complète des permissions (critère 7 + 11). |
| [test_abonnement.py](../apps/comptes/tests/test_abonnement.py) | Le Curé change d'offre, annule puis réactive ; le Trésorier **n'a pas accès** (403) ; le superadmin sans paroisse est redirigé proprement. Prouve `RoleRequisMixin` + `ExigeParoisseMixin`. |
| [test_limites_offres.py](../apps/comptes/tests/test_limites_offres.py) | Chaque offre **autorise/bloque réellement** les modules (paroissiens, communication), la navigation masque les modules non inclus, les **limites chiffrées** (3 utilisateurs pour essentiel, 7 pour standard, 2000 paroissiens) sont appliquées, un 2e Curé ne compte pas dans la limite. Prouve que les tarifs sont du code, pas du marketing. |
| [test_seed.py](../apps/comptes/tests/test_seed.py) | `seed` crée paroisse + abonnement + un compte par rôle + superadmin, les comptes **s'authentifient**, et la commande est **idempotente** (relancer ne duplique rien). Critère 13. |

---

## Questions probables du jury & réponses

**1. Comment garantissez-vous qu'une paroisse ne voie jamais les données d'une
autre ?**
Trois couches indépendantes. (1) Un manager par défaut sur chaque modèle métier
(`creer_manager_paroisse`) qui filtre automatiquement sur la paroisse courante.
(2) Un middleware qui pose cette paroisse dans une `ContextVar` à chaque requête.
(3) Des mixins de vue (`FiltrageParoisseMixin`) qui refiltrent explicitement. Le
manager profite aussi au Django Admin. C'est une défense en profondeur : même si
une couche est oubliée dans une vue, les autres tiennent.

**2. Pourquoi une `ContextVar` plutôt qu'un `threading.local` ?**
Parce qu'elle reste correcte en asynchrone (ASGI). Chaque contexte async a sa
propre valeur ; un `threading.local` fuiterait entre coroutines qui partagent un
thread. C'est un choix tourné vers l'avenir, et le `reset()` dans un `finally`
garantit qu'aucune paroisse ne fuit d'une requête à la suivante.

**3. Pourquoi un modèle `Utilisateur` custom plutôt que le `User` de Django ?**
Pour ajouter la FK `paroisse` — l'ancrage multi-tenant de chaque compte — tout en
héritant d'`AbstractUser` (mots de passe hachés, groupes, permissions). On étend
sans réécrire. Le champ est `null=True` uniquement pour le superadmin d'instance,
qui gère plusieurs paroisses.

**4. Où sont hachés les mots de passe ?**
Hérité d'`AbstractUser` : `create_user()` et `set_password()` hachent
automatiquement (PBKDF2 par défaut). `test_models.py` et `test_profil.py` le
prouvent avec `check_password()` et l'assertion `password != mot_de_passe`. Les
mots de passe temporaires d'invitation sont générés avec `secrets.token_urlsafe`,
cryptographiquement sûr.

**5. Comment sont gérés les rôles ?**
Via les **Groupes** Django : « Curé », « Secrétaire », « Trésorier », « Lecteur »,
créés par la migration [0002](../apps/comptes/migrations/0002_creer_groupes_roles.py)
(donc reproductibles sur toute installation). `RoleRequisMixin.test_func()` teste
l'appartenance ; le Curé et le superadmin ont toujours accès. Un accès refusé
renvoie un 403.

**6. La différence entre `Abonnement` et les dons de l'app finances ?**
`Abonnement` est la facturation de l'instance SaaS ParoisseConnect (quelle offre
la paroisse paie). Les `Don`/`RecuFiscal` sont la comptabilité *interne* de la
paroisse. Deux domaines distincts, volontairement dans des apps séparées.

**7. Les limites d'offre sont-elles réelles ou juste affichées ?**
Réelles. Le dictionnaire `Abonnement.LIMITES` est la source unique utilisée à la
fois par la page tarifs et par le code : `ModuleAutoriseMixin` bloque un module
hors offre (redirection), et `InvitationCreateView` refuse d'inviter au-delà de
la limite d'utilisateurs. Tout est couvert par `test_limites_offres.py`.

**8. Que se passe-t-il si une paroisse est suspendue pendant qu'un utilisateur
est connecté ?**
Deux barrières. `ConnexionForm.confirm_login_allowed()` bloque *à la connexion*.
Le middleware coupe la session *en cours* : au prochain clic, il détecte
`est_active == False`, déconnecte l'utilisateur et redirige vers la page de
connexion avec un message. Sinon la suspension n'aurait d'effet qu'à la
reconnexion. Prouvé par `test_suspension.py`.

**9. Comment l'admin isole-t-il les données puisque `Paroisse` et `Utilisateur`
n'ont pas de manager multi-tenant ?**
Justement : `Paroisse` *est* le tenant et `Utilisateur` est lu pendant l'auth,
avant qu'une paroisse courante existe. Donc leur `ModelAdmin` surcharge
`get_queryset()` pour filtrer sur `request.user.paroisse` (sauf superadmin qui
voit tout). Les autres modèles héritent de l'isolation via leur manager.

**10. Comment démontrez-vous tout ça rapidement en soutenance ?**
`make seed` (ou `python manage.py seed`) crée la paroisse Saint Raphaël et un
compte par rôle avec des identifiants affichés, dans une transaction atomique et
de façon idempotente. On se connecte alors comme `cure`, `secretaire`, etc. pour
montrer en direct les différences de permissions et de navigation.
