from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stockmovement',
            name='movement_type',
            field=models.CharField(choices=[('opening', 'Opening stock'), ('purchase', 'Purchase (stock in)'), ('sale', 'Sale (stock out)'), ('return', 'Sales return (stock in)'), ('adjustment', 'Admin adjustment')], max_length=20),
        ),
    ]
