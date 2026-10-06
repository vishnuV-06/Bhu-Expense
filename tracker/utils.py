from datetime import date, datetime
from decimal import Decimal
import calendar
from django.db.models import Sum
from django.utils import timezone
from .models import Budget, Expense, Category


def get_month_range(year: int, month: int):
    """Returns (start_date, end_date) for the given year and month."""
    start_date = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    end_date = date(year, month, last_day)
    return start_date, end_date


def parse_year_month(month_str: str = None):
    """
    Parses 'YYYY-MM' or returns current year, month as integers and date(year, month, 1).
    """
    if month_str:
        try:
            dt = datetime.strptime(month_str.strip(), '%Y-%m')
            return dt.year, dt.month, date(dt.year, dt.month, 1)
        except (ValueError, AttributeError):
            pass
    today = timezone.now().date()
    return today.year, today.month, date(today.year, today.month, 1)


def calculate_category_budget_summary(user, year: int, month: int):
    """
    Calculates detailed budget and spending breakdown for a user in a given month.
    Returns:
    - budget_items: list of dicts with budget info, spent, remaining, percentage, status, etc.
    - total_budget: Decimal
    - total_spent: Decimal
    - remaining_budget: Decimal
    - overall_percent: float
    - alert_items: list of items in warning or danger status
    - unbudgeted_categories: list of categories that had spending this month but have no budget set
    """
    start_date, end_date = get_month_range(year, month)
    month_start_date = date(year, month, 1)

    # 1. Fetch all budgets for this user and this month
    budgets = (
        Budget.objects.filter(user=user, month_year=month_start_date)
        .select_related('category')
        .order_by('category__name')
    )

    # 2. Get category-wise spending for this month for this user
    month_expenses = (
        Expense.objects.filter(
            user=user,
            date__range=(start_date, end_date)
        )
        .values('category_id')
        .annotate(total=Sum('amount'))
    )
    spent_by_category = {item['category_id']: item['total'] for item in month_expenses}

    budget_items = []
    total_budget = Decimal('0.00')
    total_budgeted_spent = Decimal('0.00')
    alert_items = []
    budgeted_category_ids = set()

    for b in budgets:
        budgeted_category_ids.add(b.category_id)
        limit = b.monthly_limit
        total_budget += limit
        spent = spent_by_category.get(b.category_id, Decimal('0.00'))
        total_budgeted_spent += spent
        remaining = limit - spent

        if limit > 0:
            percent = (spent / limit) * Decimal('100.0')
        else:
            percent = Decimal('0.0')

        percent_float = float(percent)

        if percent_float >= 100.0:
            status = 'danger'
            status_label = 'Danger'
            badge_class = 'bg-danger text-white'
            bar_class = 'bg-danger'
            over_amount = spent - limit
            alert_message = f"🔴 Budget exceeded by ₹{over_amount:,.2f} ({percent_float:.1f}%)"
        elif percent_float >= 80.0:
            status = 'warning'
            status_label = 'Warning'
            badge_class = 'bg-warning text-dark'
            bar_class = 'bg-warning'
            alert_message = f"⚠ Approaching budget limit ({percent_float:.1f}%)"
        else:
            status = 'normal'
            status_label = 'Normal'
            badge_class = 'bg-success text-white'
            bar_class = 'bg-success'
            alert_message = "Normal"

        item_data = {
            'budget': b,
            'category': b.category,
            'limit': limit,
            'spent': spent,
            'remaining': remaining,
            'percent': round(percent_float, 1),
            'display_percent': min(round(percent_float, 1), 100.0),
            'status': status,
            'status_label': status_label,
            'badge_class': badge_class,
            'bar_class': bar_class,
            'alert_message': alert_message,
            'is_over': percent_float >= 100.0,
            'over_amount': spent - limit if spent > limit else Decimal('0.00'),
        }

        budget_items.append(item_data)
        if status in ('warning', 'danger'):
            alert_items.append(item_data)

    # Calculate overall total spending in this month (including any expenses in categories without a budget)
    all_month_expenses_total = (
        Expense.objects.filter(user=user, date__range=(start_date, end_date))
        .aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    )

    remaining_budget = total_budget - all_month_expenses_total
    if total_budget > 0:
        overall_percent = float((all_month_expenses_total / total_budget) * Decimal('100.0'))
    else:
        overall_percent = 0.0

    # Unbudgeted expenses breakdown (categories with expenses but no budget this month)
    unbudgeted_items = []
    for cat_id, spent in spent_by_category.items():
        if cat_id not in budgeted_category_ids:
            cat = Category.objects.filter(id=cat_id, user=user).first()
            if cat:
                unbudgeted_items.append({
                    'category': cat,
                    'spent': spent,
                })

    return {
        'budget_items': budget_items,
        'total_budget': total_budget,
        'total_spent': all_month_expenses_total,
        'remaining_budget': remaining_budget,
        'overall_percent': round(overall_percent, 1),
        'overall_display_percent': min(round(overall_percent, 1), 100.0),
        'alert_items': alert_items,
        'unbudgeted_items': unbudgeted_items,
    }
