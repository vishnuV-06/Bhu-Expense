from django.contrib import admin
from .models import Category, Budget, Expense


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name', 'description', 'user__username')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'user', 'monthly_limit', 'month_year', 'created_at')
    list_filter = ('month_year', 'user')
    search_fields = ('category__name', 'user__username')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'user', 'amount', 'date', 'notes')
    list_filter = ('date', 'category', 'user')
    search_fields = ('category__name', 'notes', 'user__username')
