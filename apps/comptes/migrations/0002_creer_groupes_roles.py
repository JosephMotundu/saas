from django.db import migrations

NOMS_GROUPES = ["Curé", "Secrétaire", "Trésorier", "Lecteur"]


def creer_groupes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    for nom in NOMS_GROUPES:
        Group.objects.get_or_create(name=nom)


def supprimer_groupes(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=NOMS_GROUPES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("comptes", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(creer_groupes, supprimer_groupes),
    ]
