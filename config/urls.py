"""
Configuration des URLs racine du projet ParoisseConnect.
Les apps métier ajoutent leurs propres routes ici au fil des étapes.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comptes/", include("apps.comptes.urls")),
    path("paroissiens/", include("apps.paroissiens.urls")),
    path("sacrements/", include("apps.sacrements.urls")),
    path("celebrations/", include("apps.celebrations.urls")),
    path("finances/", include("apps.finances.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
