from django.contrib import admin

from .models import Don, RecuFiscal


class RecuFiscalInline(admin.StackedInline):
    model = RecuFiscal
    extra = 0
    readonly_fields = ("numero",)


@admin.register(Don)
class DonAdmin(admin.ModelAdmin):
    list_display = ("__str__", "montant", "type_don", "mode_paiement", "date", "paroisse")
    list_filter = ("paroisse", "type_don", "mode_paiement", "date")
    search_fields = ("paroissien__nom", "paroissien__prenom")
    list_select_related = ("paroissien", "paroisse")
    inlines = [RecuFiscalInline]


@admin.register(RecuFiscal)
class RecuFiscalAdmin(admin.ModelAdmin):
    list_display = ("numero", "don", "date_emission")
    search_fields = ("numero",)
    list_filter = ("date_emission",)
    readonly_fields = ("numero",)
