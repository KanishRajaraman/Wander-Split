import math
import json
from itertools import permutations


def haversine_distance(lat1, lng1, lat2, lng2):
    """Calculate distance in km between two coordinates."""
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def get_travel_time_minutes(distance_km, mode='cheapest'):
    """
    Estimate travel time based on mode.
    cheapest: walking (5 km/h) or bus (25 km/h avg with stops)
    fastest: cab/train (40 km/h avg)
    """
    if mode == 'fastest':
        speed_kmh = 40
    else:
        # Use bus for >1km, walking otherwise
        speed_kmh = 5 if distance_km < 1 else 25
    return round((distance_km / speed_kmh) * 60)


def estimate_cost(distance_km, mode='cheapest'):
    """Estimate travel cost in INR."""
    if mode == 'cheapest':
        if distance_km < 1:
            return 0  # Walking
        # Bus: ~10 INR base + 1 INR per km
        return round(10 + distance_km * 1)
    else:
        # Cab: ~50 base + 12 INR per km
        return round(50 + distance_km * 12)


def nearest_neighbor_tsp(start_lat, start_lng, pois, mode='cheapest'):
    """
    Nearest Neighbor heuristic for TSP.
    Returns optimized list of POI ids with route metadata.
    """
    if not pois:
        return [], 0, 0

    unvisited = list(pois)
    visited = []
    current_lat, current_lng = start_lat, start_lng
    total_distance = 0
    total_travel_time = 0
    segments = []

    while unvisited:
        # Find nearest unvisited POI
        nearest = None
        nearest_dist = float('inf')

        for poi in unvisited:
            dist = haversine_distance(current_lat, current_lng, poi.lat, poi.lng)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = poi

        if nearest:
            travel_time = get_travel_time_minutes(nearest_dist, mode)
            cost = estimate_cost(nearest_dist, mode)

            segments.append({
                'poi_id': nearest.id,
                'distance_km': round(nearest_dist, 2),
                'travel_time_min': travel_time,
                'buffer_time_min': 15,
                'visit_time_min': nearest.estimated_duration,
                'travel_cost': cost,
                'travel_mode_used': 'Walking' if nearest_dist < 1 and mode == 'cheapest' else
                                    ('Bus' if mode == 'cheapest' else 'Cab/Train'),
            })

            total_distance += nearest_dist
            total_travel_time += travel_time + 15  # 15-min buffer

            visited.append(nearest)
            current_lat, current_lng = nearest.lat, nearest.lng
            unvisited.remove(nearest)

    total_visit_time = sum(p.estimated_duration for p in visited)

    return visited, round(total_distance, 2), total_travel_time, total_visit_time, segments


def cluster_by_proximity(pois, num_clusters=None):
    """
    Simple geographic clustering using k-means-like approach.
    Groups nearby POIs for day-trip planning.
    """
    if not pois or len(pois) < 2:
        return [pois]

    if num_clusters is None:
        num_clusters = max(1, len(pois) // 3)

    # Initialize cluster centers using spread selection
    centers = [pois[0]]
    remaining = list(pois[1:])

    for _ in range(num_clusters - 1):
        if not remaining:
            break
        # Pick point furthest from all current centers
        max_dist = -1
        next_center = None
        for poi in remaining:
            min_dist_to_center = min(
                haversine_distance(poi.lat, poi.lng, c.lat, c.lng) for c in centers
            )
            if min_dist_to_center > max_dist:
                max_dist = min_dist_to_center
                next_center = poi
        if next_center:
            centers.append(next_center)
            remaining.remove(next_center)

    # Assign each POI to nearest center
    clusters = [[] for _ in range(len(centers))]
    for poi in pois:
        nearest_idx = min(
            range(len(centers)),
            key=lambda i: haversine_distance(poi.lat, poi.lng, centers[i].lat, centers[i].lng)
        )
        clusters[nearest_idx].append(poi)

    return [c for c in clusters if c]


def calculate_settlement(expenses, members):
    """
    Calculate who owes whom using a simplified debt settlement algorithm.
    Returns a list of transactions: {'from': user, 'to': user, 'amount': float}
    """
    balances = {member.id: 0.0 for member in members}

    for expense in expenses:
        payers = expense.payers.all()
        splitters = expense.split_among.all()

        if not splitters:
            continue

        share = float(expense.amount) / len(splitters)

        # Credit payers
        for payer in payers:
            if payer.id in balances:
                balances[payer.id] += float(expense.amount) / len(payers)

        # Debit splitters
        for person in splitters:
            if person.id in balances:
                balances[person.id] -= share

    # Settle debts
    debtors = [(uid, -bal) for uid, bal in balances.items() if bal < -0.01]
    creditors = [(uid, bal) for uid, bal in balances.items() if bal > 0.01]

    member_map = {m.id: m for m in members}
    transactions = []

    debtors = sorted(debtors, key=lambda x: x[1], reverse=True)
    creditors = sorted(creditors, key=lambda x: x[1], reverse=True)

    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_id, debt = debtors[i]
        creditor_id, credit = creditors[j]

        amount = min(debt, credit)
        if amount > 0.01:
            transactions.append({
                'from': member_map[debtor_id],
                'to': member_map[creditor_id],
                'amount': round(amount, 2),
            })

        debtors[i] = (debtor_id, debt - amount)
        creditors[j] = (creditor_id, credit - amount)

        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1

    return transactions
