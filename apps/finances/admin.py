from django.contrib import admin

from .models import Depense, Don, OffrandeMesse, RecuFiscal


class RecuFiscalInline(admin.StackedInline):
    model = RecuFiscal
    extra = 0
    readonly_fields = ("numero",)


@admin.register(Don)
class DonAdmin(admin.ModelAdmin):
    list_display = ("__str__", "montant", "devise", "type_don", "mode_paiement", "date", "paroisse")
    list_filter = ("paroisse", "devise", "type_don", "mode_paiement", "date")
    search_fields = ("paroissien__nom", "paroissien__prenom")
    list_select_related = ("paroissien", "paroisse")
    inlines = [RecuFiscalInline]


@admin.register(Depense)
class DepenseAdmin(admin.ModelAdmin):
    list_display = ("libelle", "montant", "devise", "categorie", "mode_paiement", "beneficiaire", "date", "paroisse")
    list_filter = ("paroisse", "devise", "categorie", "mode_paiement", "date")
    search_fields = ("libelle", "beneficiaire")
    list_select_related = ("paroisse",)


@admin.register(OffrandeMesse)
class OffrandeMesseAdmin(admin.ModelAdmin):
    list_display = ("__str__", "montant", "devise", "mode_paiement", "date", "paroisse")
    list_filter = ("paroisse", "devise", "mode_paiement", "date")
    search_fields = ("libelle",)
    list_select_related = ("paroisse",)


@admin.register(RecuFiscal)
class RecuFiscalAdmin(admin.ModelAdmin):
    list_display = ("numero", "don", "date_emission")
    search_fields = ("numero",)
    list_filter = ("date_emission",)
    readonly_fields = ("numero",)
