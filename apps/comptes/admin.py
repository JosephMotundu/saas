from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Paroisse, Utilisateur


@admin.register(Paroisse)
class ParoisseAdmin(admin.ModelAdmin):
    list_display = ("nom", "diocese", "ville", "telephone", "email", "date_creation")
    search_fields = ("nom", "diocese", "ville")
    list_filter = ("diocese", "ville")
    ordering = ("nom",)


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
