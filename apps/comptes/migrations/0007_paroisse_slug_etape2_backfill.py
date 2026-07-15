from django.db import migrations
from django.utils.text import slugify


def renseigner_les_slugs(apps, schema_editor):
    Paroisse = apps.get_model("comptes", "Paroisse")
    slugs_existants = set()
    for paroisse in Paroisse.objects.all():
        base = slugify(paroisse.nom) or "paroisse"
        slug = base
        compteur = 1
        while slug in slugs_existants:
            compteur += 1
            slug = f"{base}-{compteur}"
        slugs_existants.add(slug)
        paroisse.slug = slug
        paroisse.save(update_fields=["slug"])


def ne_rien_faire(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("comptes", "0006_paroisse_slug_etape1_ajout"),
    ]

    operations = [
        migrations.RunPython(renseigner_les_slugs, ne_rien_faire),
    ]
