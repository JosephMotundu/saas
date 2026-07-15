from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comptes", "0007_paroisse_slug_etape2_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paroisse",
            name="slug",
            field=models.SlugField(
                blank=True,
                help_text=(
                    "Généré automatiquement depuis le nom ; utilisé dans l'URL de la "
                    "page publique de la paroisse (communiqués visibles sans compte)."
                ),
                max_length=220,
                unique=True,
                verbose_name="identifiant public",
            ),
        ),
    ]
