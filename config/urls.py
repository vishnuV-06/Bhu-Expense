"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('tracker.urls')),
]

handler404 = 'tracker.views.error_404_view'
handler403 = 'tracker.views.error_403_view'
handler500 = 'tracker.views.error_500_view'
