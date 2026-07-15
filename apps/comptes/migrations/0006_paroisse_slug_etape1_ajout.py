from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("comptes", "0005_paroisse_avenue_paroisse_commune_paroisse_quartier_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="paroisse",
            name="slug",
            field=models.SlugField(
                blank=True,
                default="",
                help_text=(
                    "Généré automatiquement depuis le nom ; utilisé dans l'URL de la "
                    "page publique de la paroisse (communiqués visibles sans compte)."
                ),
                max_length=220,
                verbose_name="identifiant public",
            ),
        ),
    ]
