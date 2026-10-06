from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class Category(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_category_name'
            )
        ]

    def __str__(self):
        return self.name


class Budget(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    monthly_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    # Stored as the first day of the budgeted month, e.g. 2026-10-01
    month_year = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month_year', 'category__name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'category', 'month_year'],
                name='unique_user_category_month_budget'
            ),
            models.CheckConstraint(
                condition=models.Q(monthly_limit__gt=0),
                name='check_budget_monthly_limit_positive'
            )
        ]

    def __str__(self):
        return f"{self.category.name} - {self.month_display} (₹{self.monthly_limit:,.2f})"

    @property
    def month_display(self):
        return self.month_year.strftime('%B %Y')

    @property
    def month_input_value(self):
        return self.month_year.strftime('%Y-%m')


class Expense(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='check_expense_amount_positive'
            )
        ]

    def __str__(self):
        return f"{self.category.name}: ₹{self.amount:,.2f} on {self.date}"
