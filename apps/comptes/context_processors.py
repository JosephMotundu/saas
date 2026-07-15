def navigation_par_role(request):
    """Expose des indicateurs de visibilité de la navigation applicative
    selon les groupes (rôles) de l'utilisateur connecté ET selon les
    modules inclus dans l'offre de la paroisse (§7 du brief pour les
    rôles ; tarifs pour les modules — un Curé ne voit pas un module que
    son offre n'inclut pas, le rôle ne suffit pas).

    Le Curé (ou le superadmin) voit toutes les sections que son offre
    autorise. Le Lecteur a un accès en consultation à tout ce que son
    offre autorise. Les autres rôles ne voient que les sections qui
    correspondent à leurs responsabilités.
    """
    utilisateur = getattr(request, "user", None)
    if utilisateur is None or not utilisateur.is_authenticated:
        return {}

    groupes = set(utilisateur.groups.values_list("name", flat=True))
    est_cure = utilisateur.is_superuser or "Curé" in groupes
    est_lecteur = "Lecteur" in groupes

    paroisse = getattr(request, "paroisse", None)
    abonnement = getattr(paroisse, "abonnement", None) if paroisse is not None else None

    def module_autorise(nom_module):
        return abonnement is None or abonnement.module_autorise(nom_module)

    role_paroissiens = est_cure or est_lecteur or "Secrétaire" in groupes
    role_communication = est_cure or est_lecteur or "Secrétaire" in groupes

    return {
        "nav_paroissiens": role_paroissiens and module_autorise("paroissiens"),
        "nav_sacrements": est_cure or est_lecteur or "Secrétaire" in groupes,
        "nav_celebrations": est_cure or est_lecteur or "Secrétaire" in groupes,
        "nav_finances": est_cure or est_lecteur or "Trésorier" in groupes,
        "nav_communication": role_communication and module_autorise("communication"),
        "est_cure": est_cure,
    }
