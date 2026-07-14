from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Paroisse, Utilisateur


@admin.register(Paroisse)
class ParoisseAdmin(admin.ModelAdmin):
    list_display = ("nom", "diocese", "ville", "telephone", "email", "date_creation")
    search_fields = ("nom", "diocese", "ville")
    list_filter = ("diocese", "ville")
    ordering = ("nom",)

    def get_queryset(self, request):
        """Paroisse et Utilisateur ne portent pas eux-mêmes de manager
        multi-tenant automatique (Paroisse EST le tenant, et Utilisateur
        est consulté pendant l'authentification, avant qu'une paroisse
        courante ne soit connue) : l'isolation est donc appliquée ici,
        explicitement, au niveau de l'admin — §4 du brief."""
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(pk=request.user.paroisse_id)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        "username",
        "get_full_name",
        "email",
        "paroisse",
        "is_staff",
        "is_active",
    )
    list_filter = UserAdmin.list_filter + ("paroisse",)
    search_fields = UserAdmin.search_fields + ("paroisse__nom",)
    fieldsets = UserAdmin.fieldsets + (("Paroisse", {"fields": ("paroisse",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Paroisse", {"fields": ("paroisse",)}),)

    @admin.display(description="nom complet")
    def get_full_name(self, obj):
        return obj.get_full_name() or "—"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(paroisse=request.user.paroisse)
