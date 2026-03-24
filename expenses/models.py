from django.db import models
from django.contrib.auth.models import User
from trips.models import Trip


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food & Drinks'),
        ('stay', 'Stay / Accommodation'),
        ('fuel', 'Fuel / Transport'),
        ('entry', 'Entry Tickets'),
        ('shopping', 'Shopping'),
        ('misc', 'Miscellaneous'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses')
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='misc')
    payers = models.ManyToManyField(User, related_name='paid_expenses')
    split_among = models.ManyToManyField(User, related_name='split_expenses')
    date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    receipt_description = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - ₹{self.amount} ({self.trip.name})"

    def get_share_per_person(self):
        count = self.split_among.count()
        if count == 0:
            return self.amount
        return round(float(self.amount) / count, 2)

    def get_category_icon(self):
        icons = {
            'food': '🍔',
            'stay': '🏨',
            'fuel': '⛽',
            'entry': '🎟️',
            'shopping': '🛍️',
            'misc': '💰',
        }
        return icons.get(self.category, '💰')
