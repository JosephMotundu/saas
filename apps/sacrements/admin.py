from django.contrib import admin

from .models import Bapteme, Communion, Confirmation, Funerailles, Mariage, MentionMarginale


class MentionMarginaleInline(admin.TabularInline):
    model = MentionMarginale
    extra = 0
    fields = ("type_mention", "date", "reference", "paroisse")


@admin.register(Bapteme)
class BaptemeAdmin(admin.ModelAdmin):
    list_display = ("numero_acte", "paroissien", "date", "celebrant", "paroisse")
    search_fields = ("numero_acte", "paroissien__nom", "paroissien__prenom")
    list_filter = ("paroisse", "date")
    list_select_related = ("paroissien", "paroisse")
    readonly_fields = ("numero_acte",)
    inlines = [MentionMarginaleInline]


@admin.register(Communion)
class CommunionAdmin(admin.ModelAdmin):
    list_display = ("numero_acte", "paroissien", "date", "celebrant", "paroisse")
    search_fields = ("numero_acte", "paroissien__nom", "paroissien__prenom")
    list_filter = ("paroisse", "date")
    list_select_related = ("paroissien", "paroisse")
    readonly_fields = ("numero_acte",)


@admin.register(Confirmation)
class ConfirmationAdmin(admin.ModelAdmin):
    list_display = ("numero_acte", "paroissien", "date", "celebrant", "paroisse")
    search_fields = ("numero_acte", "paroissien__nom", "paroissien__prenom")
    list_filter = ("paroisse", "date")
    list_select_related = ("paroissien", "paroisse")
    readonly_fields = ("numero_acte",)


@admin.register(Funerailles)
class FunraillesAdmin(admin.ModelAdmin):
    list_display = ("numero_acte", "paroissien", "date", "celebrant", "paroisse")
    search_fields = ("numero_acte", "paroissien__nom", "paroissien__prenom")
    list_filter = ("paroisse", "date")
    list_select_related = ("paroissien", "paroisse")
    readonly_fields = ("numero_acte",)


@admin.register(Mariage)
class MariageAdmin(admin.ModelAdmin):
    list_display = ("numero_acte", "conjoint1", "conjoint2", "date", "celebrant", "paroisse")
    search_fields = ("numero_acte", "conjoint1__nom", "conjoint2__nom")
    list_filter = ("paroisse", "date")
    list_select_related = ("conjoint1", "conjoint2", "paroisse")
    readonly_fields = ("numero_acte",)


@admin.register(MentionMarginale)
class MentionMarginaleAdmin(admin.ModelAdmin):
    list_display = ("bapteme", "type_mention", "date", "paroisse")
    search_fields = ("bapteme__numero_acte", "reference")
    list_filter = ("paroisse", "type_mention")
