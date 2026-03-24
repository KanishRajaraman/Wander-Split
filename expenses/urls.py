from django.urls import path
from . import views

urlpatterns = [
    path('trip/<int:trip_pk>/', views.expense_list, name='expense_list'),
    path('trip/<int:trip_pk>/add/', views.expense_add, name='expense_add'),
    path('<int:pk>/delete/', views.expense_delete, name='expense_delete'),
]
