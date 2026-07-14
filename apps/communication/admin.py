from django.contrib import admin

from .models import Annonce


@admin.register(Annonce)
class AnnonceAdmin(admin.ModelAdmin):
    list_display = ("titre", "date_publication", "auteur", "groupe_cible", "paroisse")
    list_filter = ("paroisse", "groupe_cible", "date_publication")
    search_fields = ("titre", "contenu")
    list_select_related = ("auteur", "groupe_cible", "paroisse")
