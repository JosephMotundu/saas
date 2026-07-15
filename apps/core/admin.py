from django.contrib import admin

from .models import ContenuVitrine


@admin.register(ContenuVitrine)
class ContenuVitrineAdmin(admin.ModelAdmin):
    list_display = ("__str__", "titre_hero")

    def has_add_permission(self, request):
        # Singleton : une seule ligne, créée à la demande par charger().
        return not ContenuVitrine.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
