from django.db import models
from django.contrib.auth.models import User
import json


class Trip(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_location = models.CharField(max_length=300)
    start_lat = models.FloatField(default=0.0)
    start_lng = models.FloatField(default=0.0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_trips')
    members = models.ManyToManyField(User, related_name='trips', blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    travel_mode = models.CharField(
        max_length=20,
        choices=[('cheapest', 'Cheapest (Walk/Bus)'), ('fastest', 'Fastest (Cab/Train)')],
        default='cheapest'
    )

    def __str__(self):
        return self.name

    def get_total_spent(self):
        return sum(e.amount for e in self.expenses.all())

    def get_budget_percentage(self):
        if self.budget <= 0:
            return 0
        pct = float(self.get_total_spent()) / float(self.budget) * 100
        return min(pct, 100)

    def get_budget_color(self):
        pct = self.get_budget_percentage()
        if pct < 50:
            return 'green'
        elif pct < 80:
            return 'orange'
        return 'red'


class PointOfInterest(models.Model):
    CATEGORY_CHOICES = [
        ('attraction', 'Attraction'),
        ('food', 'Food & Drink'),
        ('accommodation', 'Accommodation'),
        ('study', 'Study-Friendly Spot'),
        ('transport', 'Transport Hub'),
        ('shopping', 'Shopping'),
        ('nature', 'Nature & Parks'),
        ('other', 'Other'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='pois')
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=400)
    lat = models.FloatField(default=0.0)
    lng = models.FloatField(default=0.0)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='attraction')
    estimated_duration = models.IntegerField(default=60, help_text='Estimated time to spend here (minutes)')
    entry_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    visit_order = models.IntegerField(default=0)
    is_study_friendly = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=False)

    class Meta:
        ordering = ['visit_order']

    def __str__(self):
        return f"{self.name} ({self.trip.name})"


class OptimizedRoute(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='optimized_route')
    poi_order = models.TextField(default='[]')  # JSON list of POI ids in order
    total_distance_km = models.FloatField(default=0)
    total_travel_time_min = models.IntegerField(default=0)
    total_visit_time_min = models.IntegerField(default=0)
    optimization_algorithm = models.CharField(max_length=50, default='nearest_neighbor')
    created_at = models.DateTimeField(auto_now=True)

    def get_poi_order(self):
        return json.loads(self.poi_order)

    def set_poi_order(self, order_list):
        self.poi_order = json.dumps(order_list)

    def get_total_time_hours(self):
        total = self.total_travel_time_min + self.total_visit_time_min
        return round(total / 60, 1)
