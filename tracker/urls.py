from django.urls import path
from . import views

urlpatterns = [
    # Home & Auth
    path('', views.home_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Categories
    path('categories/', views.category_list_view, name='category_list'),
    path('categories/create/', views.category_create_view, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit_view, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete_view, name='category_delete'),

    # Budgets
    path('budgets/', views.budget_list_view, name='budget_list'),
    path('budgets/create/', views.budget_create_view, name='budget_create'),
    path('budgets/<int:pk>/edit/', views.budget_edit_view, name='budget_edit'),
    path('budgets/<int:pk>/delete/', views.budget_delete_view, name='budget_delete'),

    # Expenses
    path('expenses/', views.expense_list_view, name='expense_list'),
    path('expenses/create/', views.expense_create_view, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit_view, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete_view, name='expense_delete'),
]
