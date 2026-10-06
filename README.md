# FinTrack - Modern Personal Expense Tracker with Budget Alerts

A complete, production-ready **Personal Expense Tracker with Automated Budget Alerts** built with Python and Django. Designed to look and feel like a modern fintech productivity web application.

---

## 🌟 Key Features

1. **Authentication & Multi-Tenant Data Isolation**
   - Standard Django authentication system (`django.contrib.auth.models.User`).
   - Strict per-user isolation: Every Category, Budget, and Expense belongs strictly to `request.user`.
   - Users cannot view, modify, or delete another user's financial data, even if IDs are altered in URLs or forms.

2. **Smart Monthly Budget Alert System**
   - **0% – 79.99% (Normal):** Positive status badge, emerald progress indicators.
   - **80% – 99.99% (Warning):** Amber warning banner: `⚠ Warning: You are approaching your budget limit.`
   - **100% and Above (Danger):** Crimson alert: `🔴 Budget exceeded by ₹X.XX (Y%)` with non-overflowing capped progress visualization.
   - Automatic calculations filtered strictly by selected month and year.

3. **Category Management**
   - Add, edit, and organize categories.
   - **Safe Deletion Protection:** If a category has existing expenses, deletion is automatically blocked with friendly guidance to edit or reassign.

4. **Transaction / Expense Management**
   - Log date, category, positive decimal amount, and notes.
   - Validates that amounts are strictly positive (rejects ₹0 and negative amounts).
   - Filter transactions by category, month, and search keywords.
   - Pagination support for fast performance.

5. **Financial Dashboard**
   - Month-by-month navigation with quick month picker.
   - Immediate high-level metrics: Total Budget, Total Spent, Remaining Allowance, Transaction Count.
   - Category budget progress bars with real-time percentage analysis.
   - Recent transactions table and unbudgeted expense insights.
   - Helpful empty states with contextual Call-To-Action buttons.

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+
- Django 5.x / 6.x

### 2. Apply Migrations
```bash
python manage.py migrate
```

### 3. (Optional) Seed Demo Data
To immediately test realistic categories, monthly budgets, and warning/danger threshold alerts:
```bash
python manage.py seed_demo_data
```
This generates two test accounts for testing user isolation:
* **Account 1:** Username `demo_user` | Password `Demo1234!`
  * Includes 5 categories, monthly budgets, and expenses showcasing normal, 84% warning, and 106% danger states.
* **Account 2:** Username `second_user` | Password `Demo1234!`
  * Includes completely distinct data to verify data isolation.

### 4. Run the Development Server
```bash
python manage.py runserver
```

Open your browser at:
```text
http://127.0.0.1:8000/
```

---

## 🧪 Automated Test Suite

Run the comprehensive automated test suite (21 unit and integration tests):
```bash
python manage.py test
```

### Verified Scenarios:
- User registration, login, and logout.
- Strict data isolation between multiple users (User A accessing User B's categories, budgets, or transactions returns 404).
- Safe category deletion (blocked when transactions exist).
- Zero and negative amounts rejection on forms and database constraints.
- Duplicate budget prevention for the same category and month.
- Budget calculation thresholds (Normal <80%, Warning 80-99.99%, Danger ≥100%).
- Monthly expense isolation (only expenses in the selected month count toward that month's budget).
