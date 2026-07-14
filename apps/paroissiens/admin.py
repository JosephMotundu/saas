from django.contrib import admin

from .models import Famille, Paroissien


@admin.register(Famille)
class FamilleAdmin(admin.ModelAdmin):
    list_display = ("nom", "ville_via_adresse", "telephone", "paroisse")
    search_fields = ("nom", "adresse")
    list_filter = ("paroisse",)

    @admin.display(description="adresse")
    def ville_via_adresse(self, obj):
        return obj.adresse or "—"


@admin.register(Paroissien)
class ParoissienAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "sexe", "date_naissance", "famille", "paroisse")
    search_fields = ("nom", "prenom", "email", "telephone")
    list_filter = ("paroisse", "sexe")
    autocomplete_fields = ["famille"]
    list_select_related = ("famille", "paroisse")
