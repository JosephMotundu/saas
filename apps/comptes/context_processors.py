def navigation_par_role(request):
    """Expose des indicateurs de visibilité de la navigation applicative
    selon les groupes (rôles) de l'utilisateur connecté.

    Le Curé (ou le superadmin) voit toutes les sections. Le Lecteur a un
    accès en consultation à tout. Les autres rôles ne voient que les
    sections qui correspondent à leurs responsabilités (§7 du brief).
    """
    utilisateur = getattr(request, "user", None)
    if utilisateur is None or not utilisateur.is_authenticated:
        return {}

    groupes = set(utilisateur.groups.values_list("name", flat=True))
    est_cure = utilisateur.is_superuser or "Curé" in groupes
    est_lecteur = "Lecteur" in groupes

    return {
        "nav_paroissiens": est_cure or est_lecteur or "Secrétaire" in groupes,
        "nav_sacrements": est_cure or est_lecteur or "Secrétaire" in groupes,
        "nav_celebrations": est_cure or est_lecteur or "Secrétaire" in groupes,
        "nav_finances": est_cure or est_lecteur or "Trésorier" in groupes,
        "nav_communication": est_cure or est_lecteur or "Secrétaire" in groupes,
        "est_cure": est_cure,
    }
