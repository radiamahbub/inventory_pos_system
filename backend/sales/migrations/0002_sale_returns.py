import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
        ('sales', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='returned_total',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Value of goods returned (= money refunded)', max_digits=14),
        ),
        migrations.AddField(
            model_name='sale',
            name='return_status',
            field=models.CharField(choices=[('none', 'Not returned'), ('partial', 'Partially returned'), ('full', 'Fully returned')], db_index=True, default='none', max_length=10),
        ),
        migrations.AddField(
            model_name='saleitem',
            name='returned_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('returned_total__gte', 0)), name='sale_returned_total_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('returned_total__lte', models.F('grand_total'))), name='sale_returned_lte_grand_total'),
        ),
        migrations.AddConstraint(
            model_name='saleitem',
            constraint=models.CheckConstraint(condition=models.Q(('returned_quantity__lte', models.F('quantity'))), name='saleitem_returned_lte_quantity'),
        ),
        migrations.CreateModel(
            name='SaleReturn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('return_number', models.CharField(editable=False, max_length=40, unique=True)),
                ('return_date', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('total_amount', models.DecimalField(decimal_places=2, help_text='Refund = value of returned goods', max_digits=14)),
                ('refund_method', models.CharField(choices=[('cash', 'Cash'), ('card', 'Card'), ('mobile_banking', 'Mobile Banking')], max_length=20)),
                ('reason', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sale_returns', to=settings.AUTH_USER_MODEL)),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='returns', to='sales.sale')),
            ],
            options={
                'ordering': ['-return_date', '-id'],
                'constraints': [models.CheckConstraint(condition=models.Q(('total_amount__gte', 0)), name='salereturn_total_gte_0')],
            },
        ),
        migrations.CreateModel(
            name='SaleReturnItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Selling price after the invoice discount is spread over the items', max_digits=12)),
                ('unit_cost', models.DecimalField(decimal_places=2, help_text='Cost snapshot (for profit reversal)', max_digits=12)),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=14)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_items', to='products.product')),
                ('sale_item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_items', to='sales.saleitem')),
                ('sale_return', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='sales.salereturn')),
            ],
            options={
                'constraints': [models.CheckConstraint(condition=models.Q(('quantity__gt', 0)), name='salereturnitem_quantity_gt_0')],
            },
        ),
    ]
