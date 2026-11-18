"""Report calculations (all done in the database / backend)."""

from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce

from config.utils import ZERO, money
from purchases.models import Purchase
from sales.models import Sale, SaleItem, SaleReturn, SaleReturnItem

DEC = DecimalField(max_digits=16, decimal_places=2)


def _sum(field):
    return Coalesce(Sum(field), Value(Decimal("0")), output_field=DEC)


def cost_of_goods_sold(sales_qs):
    """বিক্রি হওয়া পণ্যের কেনা-দাম (বিক্রির সময়ের cost snapshot অনুযায়ী)।"""
    agg = SaleItem.objects.filter(sale__in=sales_qs.values("pk")).aggregate(
        cost=Coalesce(Sum(F("quantity") * F("unit_cost"), output_field=DEC), Value(Decimal("0")), output_field=DEC)
    )
    return money(agg["cost"])


def returns_summary(returns_qs):
    """(value of returned goods, cost of those goods)."""
    total = returns_qs.aggregate(t=_sum("total_amount"))["t"]
    cost = SaleReturnItem.objects.filter(sale_return__in=returns_qs.values("pk")).aggregate(
        c=Coalesce(Sum(F("quantity") * F("unit_cost"), output_field=DEC), Value(Decimal("0")), output_field=DEC)
    )["c"]
    return money(total), money(cost)


def sales_summary(sales_qs, returns_qs=None):
    """
    `grand_total` = gross sales of the period. Returns made in the period are subtracted:
    net_sales = grand_total - returns_total, and the cost of returned goods is taken back out of
    cost_of_goods_sold, so estimated_profit stays correct.
    """
    agg = sales_qs.aggregate(
        sales_count=Count("id"),
        subtotal=_sum("subtotal"),
        discount=_sum("discount"),
        grand_total=_sum("grand_total"),
    )
    cogs = cost_of_goods_sold(sales_qs)
    grand_total = money(agg["grand_total"])
    returns_total, returns_cost = (ZERO, ZERO) if returns_qs is None else returns_summary(returns_qs)
    net_sales = grand_total - returns_total
    net_cogs = cogs - returns_cost
    return {
        "sales_count": agg["sales_count"],
        "subtotal": money(agg["subtotal"]),
        "discount": money(agg["discount"]),
        "grand_total": grand_total,
        "returns_total": returns_total,
        "net_sales": net_sales,
        "cost_of_goods_sold": net_cogs,
        "estimated_profit": money(net_sales - net_cogs),
    }


def payment_breakdown(sales_qs):
    rows = (
        sales_qs.order_by()
        .values("payment_method")
        .annotate(count=Count("id"), total=_sum("paid_amount"))  # money actually received at the sale
        .order_by("payment_method")
    )
    return [{"payment_method": r["payment_method"], "count": r["count"], "total": money(r["total"])} for r in rows]


def total_sales_amount(sales_qs):
    return money(sales_qs.aggregate(t=_sum("grand_total"))["t"])


def total_purchases(purchases_qs):
    agg = purchases_qs.aggregate(count=Count("id"), total=_sum("total_amount"))
    return agg["count"], money(agg["total"])


def sales_for_date_range(start=None, end=None):
    qs = Sale.objects.all()
    if start:
        qs = qs.filter(sale_date__date__gte=start)
    if end:
        qs = qs.filter(sale_date__date__lte=end)
    return qs


def returns_for_date_range(start=None, end=None):
    qs = SaleReturn.objects.all()
    if start:
        qs = qs.filter(return_date__date__gte=start)
    if end:
        qs = qs.filter(return_date__date__lte=end)
    return qs


def purchases_for_date_range(start=None, end=None):
    qs = Purchase.objects.all()
    if start:
        qs = qs.filter(purchase_date__gte=start)
    if end:
        qs = qs.filter(purchase_date__lte=end)
    return qs
