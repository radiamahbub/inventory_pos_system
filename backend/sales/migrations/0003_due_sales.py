import django.db.models.expressions
from django.db import migrations, models


def backfill(apps, schema_editor):
    """Everything created before this migration was paid in full, and every return was a full cash refund."""
    Sale = apps.get_model("sales", "Sale")
    SaleReturn = apps.get_model("sales", "SaleReturn")
    Sale.objects.update(paid_amount=models.F("grand_total"), refunded_total=models.F("returned_total"))
    SaleReturn.objects.update(refund_amount=models.F("total_amount"))


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        ('sales', '0002_sale_returns'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='paid_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Amount received at the time of sale', max_digits=14),
        ),
        migrations.AddField(
            model_name='sale',
            name='collected_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Due collected later (customer payments)', max_digits=14),
        ),
        migrations.AddField(
            model_name='sale',
            name='refunded_total',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Money given back to the customer so far', max_digits=14),
        ),
        migrations.AlterField(
            model_name='sale',
            name='returned_total',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Value of goods returned so far', max_digits=14),
        ),
        migrations.AddField(
            model_name='salereturn',
            name='refund_amount',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Money given back to the customer', max_digits=14),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='salereturn',
            name='due_adjusted',
            field=models.DecimalField(decimal_places=2, default=0, help_text="Part that reduced the customer's unpaid balance instead", max_digits=14),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='salereturn',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, help_text='Value of the returned goods', max_digits=14),
        ),
        migrations.AlterField(
            model_name='salereturn',
            name='refund_method',
            field=models.CharField(blank=True, choices=[('cash', 'Cash'), ('card', 'Card'), ('mobile_banking', 'Mobile Banking')], max_length=20),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('paid_amount__gte', 0)), name='sale_paid_amount_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('paid_amount__lte', models.F('grand_total'))), name='sale_paid_lte_grand_total'),
        ),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('collected_amount__gte', 0)), name='sale_collected_amount_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('refunded_total__gte', 0)), name='sale_refunded_total_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='sale',
            constraint=models.CheckConstraint(condition=models.Q(('refunded_total__lte', models.F('returned_total'))), name='sale_refunded_lte_returned'),
        ),
        migrations.AddConstraint(
            model_name='salereturn',
            constraint=models.CheckConstraint(condition=models.Q(('refund_amount__gte', 0)), name='salereturn_refund_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='salereturn',
            constraint=models.CheckConstraint(condition=models.Q(('due_adjusted__gte', 0)), name='salereturn_due_adjusted_gte_0'),
        ),
        migrations.AddConstraint(
            model_name='salereturn',
            constraint=models.CheckConstraint(condition=models.Q(('total_amount', django.db.models.expressions.CombinedExpression(models.F('refund_amount'), '+', models.F('due_adjusted')))), name='salereturn_total_equals_refund_plus_due_adjusted'),
        ),
    ]
