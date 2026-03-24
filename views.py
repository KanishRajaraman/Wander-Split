from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
import json

from .models import Trip, PointOfInterest, OptimizedRoute
from .algorithms import nearest_neighbor_tsp, cluster_by_proximity, calculate_settlement
from expenses.models import Expense


def safe_float(value, default=0.0):
    if not value or value.strip() == '':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    if not value or value.strip() == '':
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def home(request):
    if request.user.is_authenticated:
        my_trips = Trip.objects.filter(members=request.user) | Trip.objects.filter(created_by=request.user)
        my_trips = my_trips.distinct().order_by('-created_at')
    else:
        my_trips = []
    return render(request, 'trips/home.html', {'my_trips': my_trips})


@login_required
def trip_list(request):
    trips = (Trip.objects.filter(members=request.user) | Trip.objects.filter(created_by=request.user)).distinct()
    return render(request, 'trips/trip_list.html', {'trips': trips})


@login_required
def trip_create(request):
    if request.method == 'POST':
        trip = Trip.objects.create(
            name=request.POST['name'],
            description=request.POST.get('description', ''),
            start_location=request.POST['start_location'],
            start_lat=safe_float(request.POST.get('start_lat'), 0.0),
            start_lng=safe_float(request.POST.get('start_lng'), 0.0),
            budget=safe_float(request.POST.get('budget'), 0.0),
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
            travel_mode=request.POST.get('travel_mode', 'cheapest'),
            created_by=request.user,
        )
        trip.members.add(request.user)

        # Add other members by username
        for username in request.POST.getlist('members'):
            try:
                user = User.objects.get(username=username.strip())
                trip.members.add(user)
            except User.DoesNotExist:
                pass

        messages.success(request, f'Trip "{trip.name}" created successfully!')
        return redirect('trip_detail', pk=trip.pk)

    return render(request, 'trips/trip_create.html', {
        'google_maps_key': settings.GOOGLE_MAPS_API_KEY
    })


@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    pois = trip.pois.all().order_by('visit_order')
    expenses = trip.expenses.all().order_by('-created_at')

    optimized_route = None
    segments = []
    try:
        optimized_route = trip.optimized_route
    except OptimizedRoute.DoesNotExist:
        pass

    # Settlement calculations
    settlement = calculate_settlement(expenses, trip.members.all())

    budget_pct = trip.get_budget_percentage()
    budget_color = trip.get_budget_color()

    return render(request, 'trips/trip_detail.html', {
        'trip': trip,
        'pois': pois,
        'expenses': expenses,
        'optimized_route': optimized_route,
        'settlement': settlement,
        'budget_pct': budget_pct,
        'budget_color': budget_color,
        'google_maps_key': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def route_optimizer(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    pois = list(trip.pois.all())

    if request.method == 'POST':
        mode = request.POST.get('travel_mode', trip.travel_mode)
        trip.travel_mode = mode
        trip.save()

        if len(pois) < 1:
            messages.warning(request, 'Add at least one point of interest to optimize your route.')
            return redirect('route_optimizer', pk=pk)

        visited, total_dist, total_travel_time, total_visit_time, segments = nearest_neighbor_tsp(
            trip.start_lat, trip.start_lng, pois, mode
        )

        # Update visit order
        for idx, poi in enumerate(visited):
            poi.visit_order = idx + 1
            poi.save()

        # Save optimized route
        route, _ = OptimizedRoute.objects.get_or_create(trip=trip)
        route.set_poi_order([p.id for p in visited])
        route.total_distance_km = total_dist
        route.total_travel_time_min = total_travel_time
        route.total_visit_time_min = total_visit_time
        route.optimization_algorithm = 'nearest_neighbor'
        route.save()

        # Store segments in session for display
        request.session[f'segments_{pk}'] = segments
        messages.success(request, f'Route optimized! {len(visited)} stops, {round(total_dist, 1)} km total.')
        return redirect('route_optimizer', pk=pk)

    # GET
    segments = request.session.get(f'segments_{pk}', [])
    ordered_pois = []
    if segments:
        poi_map = {p.id: p for p in pois}
        for seg in segments:
            poi = poi_map.get(seg['poi_id'])
            if poi:
                ordered_pois.append({'poi': poi, 'segment': seg})

    optimized_route = None
    try:
        optimized_route = trip.optimized_route
    except OptimizedRoute.DoesNotExist:
        pass

    return render(request, 'trips/route_optimizer.html', {
        'trip': trip,
        'pois': pois,
        'ordered_pois': ordered_pois,
        'optimized_route': optimized_route,
        'google_maps_key': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def poi_add(request, trip_pk):
    trip = get_object_or_404(Trip, pk=trip_pk)
    if request.method == 'POST':
        poi = PointOfInterest.objects.create(
            trip=trip,
            name=request.POST['name'],
            address=request.POST['address'],
            lat=safe_float(request.POST.get('lat'), 0.0),
            lng=safe_float(request.POST.get('lng'), 0.0),
            category=request.POST.get('category', 'attraction'),
            estimated_duration=safe_int(request.POST.get('estimated_duration'), 60),
            entry_cost=safe_float(request.POST.get('entry_cost'), 0.0),
            notes=request.POST.get('notes', ''),
            is_study_friendly=request.POST.get('is_study_friendly') == 'on',
            has_wifi=request.POST.get('has_wifi') == 'on',
        )
        messages.success(request, f'"{poi.name}" added to your trip!')
        return redirect('route_optimizer', pk=trip_pk)

    return render(request, 'trips/poi_add.html', {
        'trip': trip,
        'google_maps_key': settings.GOOGLE_MAPS_API_KEY,
    })


@login_required
def poi_delete(request, pk):
    poi = get_object_or_404(PointOfInterest, pk=pk)
    trip_pk = poi.trip.pk
    poi.delete()
    messages.success(request, 'Point of interest removed.')
    return redirect('route_optimizer', pk=trip_pk)


@login_required
def trip_invite(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        try:
            user = User.objects.get(username=username)
            trip.members.add(user)
            messages.success(request, f'{username} added to the trip!')
        except User.DoesNotExist:
            messages.error(request, f'User "{username}" not found.')
    return redirect('trip_detail', pk=pk)


def register(request):
    from django.contrib.auth.forms import UserCreationForm
    from django.contrib.auth import login
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created! Welcome aboard 🎒')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})
