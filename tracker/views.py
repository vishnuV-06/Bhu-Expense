from datetime import date, datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import Category, Budget, Expense
from .forms import UserRegisterForm, CategoryForm, BudgetForm, ExpenseForm
from .utils import (
    parse_year_month,
    get_month_range,
    calculate_category_budget_summary,
)


def get_adjacent_months(year: int, month: int):
    """Calculates previous and next 'YYYY-MM' strings."""
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    return f"{prev_year:04d}-{prev_month:02d}", f"{next_year:04d}-{next_month:02d}"


# ==============================================================================
# Authentication Views
# ==============================================================================

def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account created successfully for {user.username}! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegisterForm()

    return render(request, 'tracker/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = AuthenticationForm()

    return render(request, 'tracker/login.html', {'form': form})


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


@login_required
def profile_view(request):
    user = request.user
    total_categories = Category.objects.filter(user=user).count()
    total_budgets = Budget.objects.filter(user=user).count()
    total_expenses_count = Expense.objects.filter(user=user).count()
    lifetime_spending = (
        Expense.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    )

    context = {
        'total_categories': total_categories,
        'total_budgets': total_budgets,
        'total_expenses_count': total_expenses_count,
        'lifetime_spending': lifetime_spending,
    }
    return render(request, 'tracker/profile.html', context)


# ==============================================================================
# Dashboard View
# ==============================================================================

@login_required
def dashboard_view(request):
    user = request.user
    month_query = request.GET.get('month')
    year, month, month_start = parse_year_month(month_query)

    start_date, end_date = get_month_range(year, month)
    prev_month_str, next_month_str = get_adjacent_months(year, month)
    current_month_str = f"{year:04d}-{month:02d}"

    # Calculate budget analytics for the month
    summary = calculate_category_budget_summary(user, year, month)

    # Count of expenses in selected month
    month_expense_count = Expense.objects.filter(
        user=user,
        date__range=(start_date, end_date)
    ).count()

    # Recent expenses (last 7 transactions overall)
    recent_expenses = (
        Expense.objects.filter(user=user)
        .select_related('category')
        .order_by('-date', '-id')[:7]
    )

    # Check if user has any categories or any expenses at all
    user_has_categories = Category.objects.filter(user=user).exists()
    user_has_any_expenses = Expense.objects.filter(user=user).exists()

    context = {
        'selected_year': year,
        'selected_month': month,
        'month_start': month_start,
        'month_name': month_start.strftime('%B %Y'),
        'current_month_str': current_month_str,
        'prev_month_str': prev_month_str,
        'next_month_str': next_month_str,
        'is_today_month': (year == timezone.now().year and month == timezone.now().month),

        # Metrics
        'total_budget': summary['total_budget'],
        'total_spent': summary['total_spent'],
        'remaining_budget': summary['remaining_budget'],
        'overall_percent': summary['overall_percent'],
        'overall_display_percent': summary['overall_display_percent'],
        'expense_count': month_expense_count,

        # Category Breakdowns & Alerts
        'budget_items': summary['budget_items'],
        'alert_items': summary['alert_items'],
        'unbudgeted_items': summary['unbudgeted_items'],
        'recent_expenses': recent_expenses,

        # State flags
        'user_has_categories': user_has_categories,
        'user_has_any_expenses': user_has_any_expenses,
    }
    return render(request, 'tracker/dashboard.html', context)


# ==============================================================================
# Category Views
# ==============================================================================

@login_required
def category_list_view(request):
    user = request.user
    # Annotate with expense count and total spent
    categories = (
        Category.objects.filter(user=user)
        .annotate(
            expense_count=Count('expenses'),
            total_spent=Sum('expenses__amount')
        )
        .order_by('name')
    )

    context = {
        'categories': categories,
    }
    return render(request, 'tracker/category_list.html', context)


@login_required
def category_create_view(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST, user=request.user)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.save()
            messages.success(request, f"✓ Category '{cat.name}' created successfully.")
            return redirect('category_list')
        else:
            messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = CategoryForm(user=request.user)

    return render(request, 'tracker/category_form.html', {
        'form': form,
        'title': 'Add New Category',
        'is_edit': False,
    })


@login_required
def category_edit_view(request, pk):
    category = get_object_or_404(Category, id=pk, user=request.user)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category, user=request.user)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"✓ Category '{cat.name}' updated successfully.")
            return redirect('category_list')
        else:
            messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = CategoryForm(instance=category, user=request.user)

    return render(request, 'tracker/category_form.html', {
        'form': form,
        'title': f'Edit Category: {category.name}',
        'category': category,
        'is_edit': True,
    })


@login_required
def category_delete_view(request, pk):
    category = get_object_or_404(Category, id=pk, user=request.user)
    expense_count = category.expenses.count()

    # Rule: If a category has existing expenses, do NOT blindly delete it.
    if expense_count > 0:
        messages.error(
            request,
            f"🔴 This category cannot be deleted because it contains {expense_count} existing expense(s). "
            f"Please edit the category instead or reassign its expenses."
        )
        return redirect('category_list')

    if request.method == 'POST':
        cat_name = category.name
        category.delete()
        messages.success(request, f"✓ Category '{cat_name}' deleted successfully.")
        return redirect('category_list')

    return render(request, 'tracker/category_confirm_delete.html', {
        'category': category,
        'expense_count': expense_count,
    })


# ==============================================================================
# Budget Views
# ==============================================================================

@login_required
def budget_list_view(request):
    user = request.user
    month_query = request.GET.get('month')
    year, month, month_start = parse_year_month(month_query)

    prev_month_str, next_month_str = get_adjacent_months(year, month)
    current_month_str = f"{year:04d}-{month:02d}"

    summary = calculate_category_budget_summary(user, year, month)
    user_has_categories = Category.objects.filter(user=user).exists()

    context = {
        'selected_year': year,
        'selected_month': month,
        'month_start': month_start,
        'month_name': month_start.strftime('%B %Y'),
        'current_month_str': current_month_str,
        'prev_month_str': prev_month_str,
        'next_month_str': next_month_str,
        'is_today_month': (year == timezone.now().year and month == timezone.now().month),

        'budget_items': summary['budget_items'],
        'total_budget': summary['total_budget'],
        'total_spent': summary['total_spent'],
        'remaining_budget': summary['remaining_budget'],
        'alert_items': summary['alert_items'],
        'unbudgeted_items': summary['unbudgeted_items'],
        'user_has_categories': user_has_categories,
    }
    return render(request, 'tracker/budget_list.html', context)


@login_required
def budget_create_view(request):
    user = request.user
    if not Category.objects.filter(user=user).exists():
        messages.warning(request, 'You need to create at least one category before setting a budget.')
        return redirect('category_create')

    initial_month = request.GET.get('month')
    initial_data = {}
    if initial_month:
        initial_data['month'] = initial_month

    if request.method == 'POST':
        form = BudgetForm(request.POST, user=user)
        if form.is_valid():
            budget = form.save()
            messages.success(
                request,
                f"✓ Budget for '{budget.category.name}' ({budget.month_display}) set to ₹{budget.monthly_limit:,.2f}."
            )
            return redirect(f"/budgets/?month={budget.month_input_value}")
        else:
            messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = BudgetForm(user=user, initial=initial_data)

    return render(request, 'tracker/budget_form.html', {
        'form': form,
        'title': 'Set Monthly Budget',
        'is_edit': False,
    })


@login_required
def budget_edit_view(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)

    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            b = form.save()
            messages.success(request, f"✓ Budget for '{b.category.name}' updated successfully.")
            return redirect(f"/budgets/?month={b.month_input_value}")
        else:
            messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = BudgetForm(instance=budget, user=request.user)

    return render(request, 'tracker/budget_form.html', {
        'form': form,
        'title': f'Edit Budget: {budget.category.name}',
        'budget': budget,
        'is_edit': True,
    })


@login_required
def budget_delete_view(request, pk):
    budget = get_object_or_404(Budget, id=pk, user=request.user)
    month_val = budget.month_input_value

    if request.method == 'POST':
        category_name = budget.category.name
        budget.delete()
        messages.success(request, f"✓ Budget for '{category_name}' removed successfully.")
        return redirect(f"/budgets/?month={month_val}")

    return render(request, 'tracker/budget_confirm_delete.html', {
        'budget': budget,
    })


# ==============================================================================
# Expense Views
# ==============================================================================

@login_required
def expense_list_view(request):
    user = request.user
    expenses_qs = Expense.objects.filter(user=user).select_related('category')

    # Filter by category if supplied
    category_id = request.GET.get('category')
    if category_id:
        expenses_qs = expenses_qs.filter(category_id=category_id)

    # Filter by month if supplied
    month_filter = request.GET.get('month')
    if month_filter:
        try:
            dt = datetime.strptime(month_filter.strip(), '%Y-%m')
            start_date, end_date = get_month_range(dt.year, dt.month)
            expenses_qs = expenses_qs.filter(date__range=(start_date, end_date))
        except ValueError:
            pass

    # Filter by search keyword
    q = request.GET.get('q', '').strip()
    if q:
        expenses_qs = expenses_qs.filter(
            Q(notes__icontains=q) | Q(category__name__icontains=q)
        )

    # Calculate filtered total sum
    total_amount = expenses_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_count = expenses_qs.count()

    # Pagination: 12 per page
    paginator = Paginator(expenses_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.filter(user=user).order_by('name')

    context = {
        'page_obj': page_obj,
        'total_amount': total_amount,
        'total_count': total_count,
        'categories': categories,
        'selected_category': category_id,
        'selected_month': month_filter or '',
        'search_query': q,
    }
    return render(request, 'tracker/expense_list.html', context)


@login_required
def expense_create_view(request):
    user = request.user
    if not Category.objects.filter(user=user).exists():
        messages.warning(request, 'Please create at least one category before recording an expense.')
        return redirect('category_create')

    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=user)
        if form.is_valid():
            expense = form.save()
            messages.success(
                request,
                f"✓ Expense of ₹{expense.amount:,.2f} recorded in '{expense.category.name}'."
            )
            return redirect('expense_list')
        else:
            messages.error(request, 'Please correct the highlighted fields.')
    else:
        initial_data = {}
        category_id = request.GET.get('category')
        if category_id:
            initial_data['category'] = category_id
        form = ExpenseForm(user=user, initial=initial_data)

    return render(request, 'tracker/expense_form.html', {
        'form': form,
        'title': 'Record New Expense',
        'is_edit': False,
    })


@login_required
def expense_edit_view(request, pk):
    expense = get_object_or_404(Expense, id=pk, user=request.user)

    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            exp = form.save()
            messages.success(request, f"✓ Expense of ₹{exp.amount:,.2f} updated successfully.")
            return redirect('expense_list')
        else:
            messages.error(request, 'Please correct the highlighted fields.')
    else:
        form = ExpenseForm(instance=expense, user=request.user)

    return render(request, 'tracker/expense_form.html', {
        'form': form,
        'title': f'Edit Expense: {expense.category.name}',
        'expense': expense,
        'is_edit': True,
    })


@login_required
def expense_delete_view(request, pk):
    expense = get_object_or_404(Expense, id=pk, user=request.user)

    if request.method == 'POST':
        amount = expense.amount
        cat_name = expense.category.name
        expense.delete()
        messages.success(request, f"✓ Expense of ₹{amount:,.2f} ({cat_name}) deleted successfully.")
        return redirect('expense_list')

    return render(request, 'tracker/expense_confirm_delete.html', {
        'expense': expense,
    })


# ==============================================================================
# Error Handlers
# ==============================================================================

def error_404_view(request, exception=None):
    return render(request, '404.html', status=404)


def error_403_view(request, exception=None):
    return render(request, '403.html', status=403)


def error_500_view(request):
    return render(request, '500.html', status=500)
