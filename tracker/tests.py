from decimal import Decimal
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from tracker.models import Category, Budget, Expense
from tracker.forms import ExpenseForm, BudgetForm, CategoryForm
from tracker.utils import calculate_category_budget_summary


class UserAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!'
        )

    def test_unauthenticated_user_redirected_to_login(self):
        urls = [
            reverse('dashboard'),
            reverse('category_list'),
            reverse('budget_list'),
            reverse('expense_list'),
            reverse('expense_create'),
            reverse('budget_create'),
            reverse('category_create'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/', response.url)

    def test_login_flow(self):
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_registration_flow(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_logout_flow(self):
        self.client.login(username='testuser', password='Password123!')
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))


class UserDataIsolationTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', password='password123')
        self.bob = User.objects.create_user(username='bob', password='password123')

        # Alice's data
        self.alice_cat = Category.objects.create(user=self.alice, name='Alice Food')
        self.alice_budget = Budget.objects.create(
            user=self.alice,
            category=self.alice_cat,
            monthly_limit=Decimal('5000.00'),
            month_year=date(2026, 10, 1)
        )
        self.alice_expense = Expense.objects.create(
            user=self.alice,
            category=self.alice_cat,
            amount=Decimal('450.00'),
            date=date(2026, 10, 5)
        )

        # Bob's data
        self.bob_cat = Category.objects.create(user=self.bob, name='Bob Gadgets')
        self.bob_budget = Budget.objects.create(
            user=self.bob,
            category=self.bob_cat,
            monthly_limit=Decimal('10000.00'),
            month_year=date(2026, 10, 1)
        )
        self.bob_expense = Expense.objects.create(
            user=self.bob,
            category=self.bob_cat,
            amount=Decimal('1500.00'),
            date=date(2026, 10, 5)
        )

    def test_alice_cannot_view_bob_categories(self):
        client = Client()
        client.login(username='alice', password='password123')
        response = client.get(reverse('category_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Food')
        self.assertNotContains(response, 'Bob Gadgets')

    def test_alice_cannot_edit_bob_category(self):
        client = Client()
        client.login(username='alice', password='password123')
        # Direct attempt to access Bob's category edit view by ID
        response = client.get(reverse('category_edit', args=[self.bob_cat.id]))
        self.assertEqual(response.status_code, 404)

        # Direct POST attempt to tamper with Bob's category
        post_response = client.post(reverse('category_edit', args=[self.bob_cat.id]), {
            'name': 'Hacked Category'
        })
        self.assertEqual(post_response.status_code, 404)
        self.bob_cat.refresh_from_db()
        self.assertEqual(self.bob_cat.name, 'Bob Gadgets')

    def test_alice_cannot_delete_bob_category(self):
        client = Client()
        client.login(username='alice', password='password123')
        response = client.post(reverse('category_delete', args=[self.bob_cat.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Category.objects.filter(id=self.bob_cat.id).exists())

    def test_alice_cannot_view_or_modify_bob_budget(self):
        client = Client()
        client.login(username='alice', password='password123')

        # List view
        response = client.get(reverse('budget_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alice Food')
        self.assertNotContains(response, 'Bob Gadgets')

        # Edit Bob's budget
        edit_response = client.get(reverse('budget_edit', args=[self.bob_budget.id]))
        self.assertEqual(edit_response.status_code, 404)

        # Delete Bob's budget
        del_response = client.post(reverse('budget_delete', args=[self.bob_budget.id]))
        self.assertEqual(del_response.status_code, 404)
        self.assertTrue(Budget.objects.filter(id=self.bob_budget.id).exists())

    def test_alice_cannot_view_or_modify_bob_expense(self):
        client = Client()
        client.login(username='alice', password='password123')

        # List view
        response = client.get(reverse('expense_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '450.00')
        self.assertNotContains(response, '1500.00')

        # Edit Bob's expense
        edit_response = client.get(reverse('expense_edit', args=[self.bob_expense.id]))
        self.assertEqual(edit_response.status_code, 404)

        # Delete Bob's expense
        del_response = client.post(reverse('expense_delete', args=[self.bob_expense.id]))
        self.assertEqual(del_response.status_code, 404)
        self.assertTrue(Expense.objects.filter(id=self.bob_expense.id).exists())

    def test_expense_and_budget_form_dropdown_restricted_to_user_categories(self):
        exp_form = ExpenseForm(user=self.alice)
        self.assertIn(self.alice_cat, exp_form.fields['category'].queryset)
        self.assertNotIn(self.bob_cat, exp_form.fields['category'].queryset)

        budget_form = BudgetForm(user=self.alice)
        self.assertIn(self.alice_cat, budget_form.fields['category'].queryset)
        self.assertNotIn(self.bob_cat, budget_form.fields['category'].queryset)


class CategoryManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='catuser', password='password123')
        self.client = Client()
        self.client.login(username='catuser', password='password123')

    def test_create_category(self):
        response = self.client.post(reverse('category_create'), {
            'name': 'Groceries',
            'description': 'Supermarket and grocery spending'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(user=self.user, name='Groceries').exists())

    def test_prevent_duplicate_category_for_same_user(self):
        Category.objects.create(user=self.user, name='Travel')
        form = CategoryForm(data={'name': 'travel'}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("already have a category", str(form.errors))

    def test_category_deletion_blocked_when_expenses_exist(self):
        cat = Category.objects.create(user=self.user, name='Shopping')
        Expense.objects.create(
            user=self.user,
            category=cat,
            amount=Decimal('200.00'),
            date=date.today()
        )

        # Attempt to delete via POST
        response = self.client.post(reverse('category_delete', args=[cat.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        # Verify category still exists
        self.assertTrue(Category.objects.filter(id=cat.id).exists())
        # Verify clear message was shown
        self.assertContains(response, 'cannot be deleted because it contains')

    def test_category_deletion_allowed_when_no_expenses(self):
        cat = Category.objects.create(user=self.user, name='Empty Category')
        response = self.client.post(reverse('category_delete', args=[cat.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(id=cat.id).exists())


class BudgetAndExpenseValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='valuser', password='password123')
        self.cat = Category.objects.create(user=self.user, name='Food')
        self.client = Client()
        self.client.login(username='valuser', password='password123')

    def test_reject_zero_and_negative_expense_amount(self):
        # Zero amount
        form_zero = ExpenseForm(data={
            'category': self.cat.id,
            'amount': '0.00',
            'date': '2026-10-06'
        }, user=self.user)
        self.assertFalse(form_zero.is_valid())
        self.assertIn('amount', form_zero.errors)

        # Negative amount
        form_neg = ExpenseForm(data={
            'category': self.cat.id,
            'amount': '-150.00',
            'date': '2026-10-06'
        }, user=self.user)
        self.assertFalse(form_neg.is_valid())
        self.assertIn('amount', form_neg.errors)

    def test_reject_zero_and_negative_budget_amount(self):
        form_zero = BudgetForm(data={
            'category': self.cat.id,
            'monthly_limit': '0.00',
            'month': '2026-10'
        }, user=self.user)
        self.assertFalse(form_zero.is_valid())
        self.assertIn('monthly_limit', form_zero.errors)

        form_neg = BudgetForm(data={
            'category': self.cat.id,
            'monthly_limit': '-500.00',
            'month': '2026-10'
        }, user=self.user)
        self.assertFalse(form_neg.is_valid())
        self.assertIn('monthly_limit', form_neg.errors)

    def test_reject_duplicate_budget_for_same_month(self):
        Budget.objects.create(
            user=self.user,
            category=self.cat,
            monthly_limit=Decimal('5000.00'),
            month_year=date(2026, 10, 1)
        )
        form_dup = BudgetForm(data={
            'category': self.cat.id,
            'monthly_limit': '6000.00',
            'month': '2026-10'
        }, user=self.user)
        self.assertFalse(form_dup.is_valid())
        self.assertIn("already exists", str(form_dup.errors))


class BudgetThresholdAndMonthlyCalculationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='calcuser', password='password123')
        self.cat_food = Category.objects.create(user=self.user, name='Food')
        self.cat_shop = Category.objects.create(user=self.user, name='Shopping')

        # Food budget: 5,000 for October 2026
        self.budget_food = Budget.objects.create(
            user=self.user,
            category=self.cat_food,
            monthly_limit=Decimal('5000.00'),
            month_year=date(2026, 10, 1)
        )
        # Shopping budget: 5,000 for October 2026
        self.budget_shop = Budget.objects.create(
            user=self.user,
            category=self.cat_shop,
            monthly_limit=Decimal('5000.00'),
            month_year=date(2026, 10, 1)
        )

    def test_normal_budget_threshold_below_80_percent(self):
        # 50% spending: ₹2,500
        Expense.objects.create(
            user=self.user,
            category=self.cat_food,
            amount=Decimal('2500.00'),
            date=date(2026, 10, 6)
        )
        summary = calculate_category_budget_summary(self.user, 2026, 10)
        food_item = next(i for i in summary['budget_items'] if i['category'].name == 'Food')

        self.assertEqual(food_item['spent'], Decimal('2500.00'))
        self.assertEqual(food_item['remaining'], Decimal('2500.00'))
        self.assertEqual(food_item['percent'], 50.0)
        self.assertEqual(food_item['status'], 'normal')
        self.assertEqual(food_item['status_label'], 'Normal')

    def test_warning_budget_threshold_80_to_100_percent(self):
        # 84% spending: ₹4,200 (₹5,000 limit)
        Expense.objects.create(
            user=self.user,
            category=self.cat_food,
            amount=Decimal('4200.00'),
            date=date(2026, 10, 6)
        )
        summary = calculate_category_budget_summary(self.user, 2026, 10)
        food_item = next(i for i in summary['budget_items'] if i['category'].name == 'Food')

        self.assertEqual(food_item['percent'], 84.0)
        self.assertEqual(food_item['status'], 'warning')
        self.assertEqual(food_item['status_label'], 'Warning')
        self.assertIn("Approaching budget limit", food_item['alert_message'])
        self.assertEqual(len(summary['alert_items']), 1)

    def test_danger_budget_threshold_at_and_above_100_percent(self):
        # 106% spending: ₹5,300 (₹5,000 limit)
        Expense.objects.create(
            user=self.user,
            category=self.cat_shop,
            amount=Decimal('5300.00'),
            date=date(2026, 10, 6)
        )
        summary = calculate_category_budget_summary(self.user, 2026, 10)
        shop_item = next(i for i in summary['budget_items'] if i['category'].name == 'Shopping')

        self.assertEqual(shop_item['percent'], 106.0)
        self.assertEqual(shop_item['display_percent'], 100.0)  # visual progress bar capped at 100%
        self.assertEqual(shop_item['status'], 'danger')
        self.assertEqual(shop_item['status_label'], 'Danger')
        self.assertTrue(shop_item['is_over'])
        self.assertEqual(shop_item['over_amount'], Decimal('300.00'))
        self.assertIn("Budget exceeded", shop_item['alert_message'])

    def test_monthly_calculation_ignores_other_months(self):
        # Food expense in September 2026: ₹3,000
        Expense.objects.create(
            user=self.user,
            category=self.cat_food,
            amount=Decimal('3000.00'),
            date=date(2026, 9, 20)
        )
        # Food expense in October 2026: ₹1,000
        Expense.objects.create(
            user=self.user,
            category=self.cat_food,
            amount=Decimal('1000.00'),
            date=date(2026, 10, 5)
        )
        # Food expense in November 2026: ₹2,000
        Expense.objects.create(
            user=self.user,
            category=self.cat_food,
            amount=Decimal('2000.00'),
            date=date(2026, 11, 2)
        )

        summary_oct = calculate_category_budget_summary(self.user, 2026, 10)
        food_oct = next(i for i in summary_oct['budget_items'] if i['category'].name == 'Food')

        # Only October's ₹1,000 should be counted, not September or November!
        self.assertEqual(food_oct['spent'], Decimal('1000.00'))
        self.assertEqual(food_oct['remaining'], Decimal('4000.00'))
        self.assertEqual(food_oct['percent'], 20.0)
