from django.contrib import admin
from .models import Trip, PointOfInterest, OptimizedRoute

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'budget', 'start_date', 'travel_mode']
    filter_horizontal = ['members']

@admin.register(PointOfInterest)
class POIAdmin(admin.ModelAdmin):
    list_display = ['name', 'trip', 'category', 'visit_order', 'entry_cost']

admin.site.register(OptimizedRoute)
