import csv
import logging
import os
import time
from geopy import Nominatim
from django.core.management.base import BaseCommand
from optimizer.models import FuelStation


logging.basicConfig(level=logging.INFO)

class Command(BaseCommand):
    help = 'Load fuel prices from CSV'

    def handle(self, *args, **kwargs):
        with open(os.environ.get("FUEL_PRICES_PATH"), 'r') as file:
            reader = csv.DictReader(file)
            geolocator = Nominatim(user_agent="fuel_api")
            prices_count = 0
            for row in reader:
                address = f"{row['Address']}, {row['City']}, {row['State']}, USA"
                try:
                    location = geolocator.geocode(address)

                    FuelStation.objects.update_or_create(
                        truck_stop_id=row['OPIS Truckstop ID'],
                        defaults={
                            "name": row['Truckstop Name'],
                            "address": row['Address'],
                            "city": row['City'],
                            "state": row['State'],
                            "retail_price": row['Retail Price'],
                            "latitude": location.latitude if location else None,
                            "longitude": location.longitude if location else None,
                        },
                    )
                    prices_count += 1
                    self.stdout.write(self.style.SUCCESS(f'loaded {prices_count}'))
                    time.sleep(1)  #
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error geocoding {row["Truckstop Name"]}: {str(e)}'))
        self.stdout.write(self.style.SUCCESS('Fuel prices loaded successfully'))