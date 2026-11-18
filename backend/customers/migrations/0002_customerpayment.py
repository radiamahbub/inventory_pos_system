import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(editable=False, max_length=40, unique=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('payment_method', models.CharField(choices=[('cash', 'Cash'), ('card', 'Card'), ('mobile_banking', 'Mobile Banking')], default='cash', max_length=20)),
                ('payment_date', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customer_payments', to=settings.AUTH_USER_MODEL)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payments', to='customers.customer')),
            ],
            options={
                'ordering': ['-payment_date', '-id'],
                'constraints': [models.CheckConstraint(condition=models.Q(('amount__gt', 0)), name='customerpayment_amount_gt_0')],
            },
        ),
    ]
