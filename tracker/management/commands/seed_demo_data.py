from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from tracker.models import Category, Budget, Expense


class Command(BaseCommand):
    help = 'Seeds realistic sample users, categories, budgets, and expenses for demo testing.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        year = today.year
        month = today.month
        first_of_month = date(year, month, 1)

        self.stdout.write(self.style.NOTICE("Setting up demo users and data..."))

        # User 1: Primary Demo User
        u1, created = User.objects.get_or_create(
            username='demo_user',
            defaults={
                'email': 'demo@example.com',
                'first_name': 'Vishnu',
                'last_name': 'Sharma',
            }
        )
        u1.set_password('Demo1234!')
        u1.save()

        # Clean old demo data for u1
        Category.objects.filter(user=u1).delete()

        # Categories for User 1
        cat_food = Category.objects.create(
            user=u1,
            name='Food & Dining',
            description='Groceries, restaurants, snacks, and food delivery'
        )
        cat_shopping = Category.objects.create(
            user=u1,
            name='Shopping & Lifestyle',
            description='Clothing, electronics, personal care, and gadgets'
        )
        cat_housing = Category.objects.create(
            user=u1,
            name='Housing & Utilities',
            description='Rent, electricity, water, and broadband'
        )
        cat_travel = Category.objects.create(
            user=u1,
            name='Travel & Commute',
            description='Fuel, bus, train, metro, and taxi rides'
        )
        cat_health = Category.objects.create(
            user=u1,
            name='Healthcare & Fitness',
            description='Medicine, gym membership, doctor checkups'
        )

        # Budgets for User 1
        # 1. Food: ₹5,000 limit -> will spend ₹4,200 (84% Warning)
        Budget.objects.create(
            user=u1,
            category=cat_food,
            monthly_limit=Decimal('5000.00'),
            month_year=first_of_month
        )
        # 2. Shopping: ₹5,000 limit -> will spend ₹5,300 (106% Danger / Exceeded)
        Budget.objects.create(
            user=u1,
            category=cat_shopping,
            monthly_limit=Decimal('5000.00'),
            month_year=first_of_month
        )
        # 3. Housing: ₹15,000 limit -> will spend ₹11,200 (74.7% Normal)
        Budget.objects.create(
            user=u1,
            category=cat_housing,
            monthly_limit=Decimal('15000.00'),
            month_year=first_of_month
        )
        # 4. Travel: ₹3,000 limit -> will spend ₹1,500 (50.0% Normal)
        Budget.objects.create(
            user=u1,
            category=cat_travel,
            monthly_limit=Decimal('3000.00'),
            month_year=first_of_month
        )

        # Expenses for User 1
        # Food Expenses (Total ₹4,200 -> 84%)
        Expense.objects.create(user=u1, category=cat_food, amount=Decimal('450.00'), date=today, notes='Team lunch at cafe')
        Expense.objects.create(user=u1, category=cat_food, amount=Decimal('1250.00'), date=today, notes='Weekly supermarket grocery haul')
        Expense.objects.create(user=u1, category=cat_food, amount=Decimal('800.00'), date=today, notes='Dinner with family')
        Expense.objects.create(user=u1, category=cat_food, amount=Decimal('700.00'), date=today, notes='Fresh fruits and vegetables')
        Expense.objects.create(user=u1, category=cat_food, amount=Decimal('1000.00'), date=today, notes='Weekend dining out')

        # Shopping Expenses (Total ₹5,300 -> 106% Exceeded)
        Expense.objects.create(user=u1, category=cat_shopping, amount=Decimal('2500.00'), date=today, notes='New running shoes')
        Expense.objects.create(user=u1, category=cat_shopping, amount=Decimal('1800.00'), date=today, notes='Winter jackets and shirts')
        Expense.objects.create(user=u1, category=cat_shopping, amount=Decimal('1000.00'), date=today, notes='Wireless earbuds')

        # Housing Expenses (Total ₹11,200 -> 74.7%)
        Expense.objects.create(user=u1, category=cat_housing, amount=Decimal('10000.00'), date=today, notes='Monthly apartment rent')
        Expense.objects.create(user=u1, category=cat_housing, amount=Decimal('1200.00'), date=today, notes='Electricity & high-speed Wi-Fi bill')

        # Travel Expenses (Total ₹1,500 -> 50%)
        Expense.objects.create(user=u1, category=cat_travel, amount=Decimal('1000.00'), date=today, notes='Fuel / Petrol refill')
        Expense.objects.create(user=u1, category=cat_travel, amount=Decimal('500.00'), date=today, notes='Metro transit card recharge')

        # Unbudgeted Healthcare Expense (₹650)
        Expense.objects.create(user=u1, category=cat_health, amount=Decimal('650.00'), date=today, notes='Prescription medicines')

        # User 2: Second User to prove isolation
        u2, _ = User.objects.get_or_create(
            username='second_user',
            defaults={'email': 'second@example.com', 'first_name': 'Priya'}
        )
        u2.set_password('Demo1234!')
        u2.save()

        Category.objects.filter(user=u2).delete()

        cat_office = Category.objects.create(user=u2, name='Office Supplies', description='Stationery and workspace tools')
        Budget.objects.create(user=u2, category=cat_office, monthly_limit=Decimal('4000.00'), month_year=first_of_month)
        Expense.objects.create(user=u2, category=cat_office, amount=Decimal('1200.00'), date=today, notes='Printer paper and notebooks')

        self.stdout.write(self.style.SUCCESS("Demo data successfully created!"))
        self.stdout.write(self.style.SUCCESS("  User 1: demo_user / Demo1234!"))
        self.stdout.write(self.style.SUCCESS("  User 2: second_user / Demo1234!"))
