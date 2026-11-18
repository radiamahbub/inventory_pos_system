from django.db import migrations


def superusers_to_admin(apps, schema_editor):
    """আগে থেকে তৈরি superuser-রা যেন Admin role পায়।"""
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True).update(role="admin")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_user_managers_user_role")]
    operations = [migrations.RunPython(superusers_to_admin, migrations.RunPython.noop)]
