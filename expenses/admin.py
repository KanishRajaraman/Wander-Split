from django.contrib import admin
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['title', 'trip', 'amount', 'category', 'created_at']
    filter_horizontal = ['payers', 'split_among']
