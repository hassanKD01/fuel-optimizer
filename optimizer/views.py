import json
import logging

import openrouteservice
from openrouteservice.directions import directions
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from geopy.distance import geodesic

from optimizer.exceptions import NoFuelStationInRange

logging.basicConfig(level=logging.INFO)
client = openrouteservice.Client(key=settings.ORS_API_KEY)

@csrf_exempt
def optimize_fuel(request):
    if request.method == 'POST':
        body = request.body.decode('utf-8')
        json_body = json.loads(body)
        start_coords = json_body.get("start")
        finish_coords = json_body.get("finish")

        if not start_coords or not finish_coords:
            return JsonResponse({"error": "Both start and finish locations are required"}, status=400)

        try:
            route_data = directions(client, coordinates=[start_coords, finish_coords], profile='driving-car', format='geojson')
        except Exception as e:
            logging.exception("Fetching directions failed for start: %s, finish: %s", start_coords, finish_coords)
            return JsonResponse({'error': f'Routing failed: {str(e)}'}, status=400)
        route = route_data["features"][0]["geometry"]["coordinates"]
        try:
            fuel_stops = calculate_fuel_stops(route)
        except NoFuelStationInRange as e:
            logging.error(str(e))
            return JsonResponse({
                'route': route_data["features"],
                'fuel_stops': [],
                'total_cost': ""
            })
        total_cost = calculate_total_cost(fuel_stops)

        return JsonResponse({
            'route': route_data["features"],
            'fuel_stops': fuel_stops,
            'total_cost': total_cost
        })

    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)


def calculate_fuel_stops(coordinates):
    fuel_stops = []
    max_range = 500
    fuel_efficiency = 10
    tank_capacity = max_range / fuel_efficiency

    route_coords = [(coord[1], coord[0]) for coord in coordinates]

    current_fuel = tank_capacity
    current_location = route_coords[0]
    total_distance = 0

    for i in range(1, len(route_coords)):
        next_location = route_coords[i]
        distance = geodesic(current_location, next_location).miles
        total_distance += distance

        if distance > current_fuel * fuel_efficiency:
            fuel_station = find_nearest_fuel_station(current_location, current_fuel * fuel_efficiency)
            if fuel_station:
                fuel_stops.append({
                    **fuel_station,
                    'distance_from_previous_stop': total_distance
                })
                current_fuel = tank_capacity
                current_location = (fuel_station['latitude'], fuel_station['longitude'])
                total_distance = 0
            else:
                raise NoFuelStationInRange("No fuel station found within range")

        current_fuel -= distance / fuel_efficiency
        current_location = next_location

    return fuel_stops


def find_nearest_fuel_station(location, max_distance):
    """
    Find the nearest fuel station within a given distance.
    """
    from optimizer.models import FuelStation
    from geopy.distance import geodesic

    fuel_stations = FuelStation.objects.filter(longitude__isnull=False, latitude__isnull=False)

    nearest_station = None
    min_distance = float('inf')

    for station in fuel_stations:
        station_location = (station.latitude, station.longitude)
        distance = geodesic(location, station_location).miles

        if distance <= max_distance and distance < min_distance:
            nearest_station = {
                'truckstop_name': station.truck_stop_id,
                'address': station.address,
                'city': station.city,
                'state': station.state,
                'retail_price': station.retail_price,
                'latitude': station.latitude,
                'longitude': station.longitude
            }
            min_distance = distance

    return nearest_station


def calculate_total_cost(fuel_stops):
    fuel_efficiency = 10
    total_cost = 0

    for i in range(len(fuel_stops)):
        if i == 0:
            distance = fuel_stops[i]['distance_from_previous_stop']
        else:
            distance = fuel_stops[i]['distance_from_previous_stop'] - fuel_stops[i - 1]['distance_from_previous_stop']

        fuel_needed = distance / fuel_efficiency

        total_cost += fuel_needed * fuel_stops[i]['retail_price']

    return total_cost
