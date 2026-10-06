from datetime import datetime, date
from decimal import Decimal
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import Category, Budget, Expense


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'name@example.com',
            'autocomplete': 'email',
        }),
        help_text='A valid email address is required for your account.'
    )
    first_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name (optional)',
        })
    )
    last_name = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name (optional)',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'autocomplete': 'username',
        })
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Create password',
                'autocomplete': 'new-password',
            })
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({
                'class': 'form-control',
                'placeholder': 'Confirm password',
                'autocomplete': 'new-password',
            })

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Groceries, Rent, Utilities, Dining Out',
                'autofocus': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional brief notes about what this category covers',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Category name cannot be empty.')

        # Check for case-insensitive duplicate for this user
        qs = Category.objects.filter(user=self.user, name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(f"You already have a category named '{name}'.")

        return name


class BudgetForm(forms.ModelForm):
    month = forms.CharField(
        widget=forms.TextInput(attrs={
            'type': 'month',
            'class': 'form-control',
            'placeholder': 'YYYY-MM',
        }),
        help_text='Select the month and year for this budget limit.'
    )

    class Meta:
        model = Budget
        fields = ['category', 'monthly_limit', 'month']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'monthly_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'e.g. 5000.00',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # Strictly restrict category queryset to user
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user).order_by('name')
            self.fields['category'].empty_label = '-- Select a Category --'

        # If editing, set the initial month in 'YYYY-MM' format
        if self.instance and self.instance.pk and self.instance.month_year:
            self.fields['month'].initial = self.instance.month_year.strftime('%Y-%m')
        else:
            # Default to current month
            today = timezone.now().date()
            self.fields['month'].initial = today.strftime('%Y-%m')

    def clean_monthly_limit(self):
        limit = self.cleaned_data.get('monthly_limit')
        if limit is None or limit <= Decimal('0.00'):
            raise forms.ValidationError('Monthly budget limit must be greater than zero (e.g. ₹0.01 or more).')
        return limit

    def clean_month(self):
        month_str = self.cleaned_data.get('month', '').strip()
        try:
            dt = datetime.strptime(month_str, '%Y-%m')
            # Return first day of month
            return date(dt.year, dt.month, 1)
        except (ValueError, TypeError):
            raise forms.ValidationError('Please provide a valid month in YYYY-MM format.')

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        month_date = cleaned_data.get('month')

        if category and month_date and self.user:
            # Check for existing budget for this category and month
            qs = Budget.objects.filter(
                user=self.user,
                category=category,
                month_year=month_date
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                month_display = month_date.strftime('%B %Y')
                raise forms.ValidationError(
                    f"A budget for '{category.name}' in {month_display} already exists. "
                    f"Please edit the existing budget instead."
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.user
        instance.month_year = self.cleaned_data['month']
        if commit:
            instance.save()
        return instance


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'date', 'notes']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'e.g. 450.00',
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description (e.g., Grocery shopping at supermarket)',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # Restrict category choices strictly to logged-in user
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user).order_by('name')
            self.fields['category'].empty_label = '-- Select a Category --'

        # Default date to today if creating new
        if not self.instance or not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= Decimal('0.00'):
            raise forms.ValidationError('Expense amount must be greater than zero. ₹0 and negative amounts are not permitted.')
        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.user = self.user
        if commit:
            instance.save()
        return instance
