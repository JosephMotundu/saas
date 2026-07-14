from django.contrib import admin

from .models import Celebration, IntentionMesse


class IntentionMesseInline(admin.TabularInline):
    model = IntentionMesse
    extra = 0
    fields = ("demandeur", "intention", "montant_offrande", "statut")


@admin.register(Celebration)
class CelebrationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type_celebration", "date", "heure", "celebrant", "paroisse")
    list_filter = ("paroisse", "type_celebration", "date")
    search_fields = ("celebrant", "lieu")
    inlines = [IntentionMesseInline]


@admin.register(IntentionMesse)
class IntentionMesseAdmin(admin.ModelAdmin):
    list_display = ("demandeur", "intention", "statut", "montant_offrande", "celebration", "paroisse")
    list_filter = ("paroisse", "statut")
    search_fields = ("demandeur", "intention")
    list_select_related = ("celebration", "paroisse")
