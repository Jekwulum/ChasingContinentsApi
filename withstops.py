import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
import re
import itertools
from amadeus import Client, ResponseError

# Load Amadeus client globally
load_dotenv()
amadeus = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

# Hardcoded destinations categorized by continent
south_america_destinations = ["SCL"]
north_america_destinations = ["MIA", "PTY", "LAX", "SFO", "SAN", "TIJ"]
europe_destinations = ["MAD", "LIS", "BCN", "ORY", "CMN"]
africa_destinations = ["CMN", "CAI"]
asia_destinations = ["DOH", "DXB", "KUL"]
australia_destinations = ["PER"]

# Editable buffer times for each IATA code (in hours)
buffer_hours = {
    "SAN": 2, "TIJ": 2, "BCN": 2, "ORY": 2, "KUL": 2,
    "SCL": 0.5, "PUQ": 1.5, "PTY": 2, "LIS": 2, "SFO": 2,
    "MIA": 2, "JFK": 2, "LAX": 2, "YYZ": 2.8, "DFW": 1.7,
    "MAD": 2, "LHR": 2.1, "CDG": 1.8, "FRA": 2.5, "AMS": 2.0,
    "CMN": 2, "JNB": 2.7, "LOS": 1.9, "CAI": 2, "ADD": 1.5,
    "DOH": 1.5, "DXB": 2, "DEL": 1.6, "SIN": 2.3, "HND": 2.0,
    "PER": 2, "SYD": 2.8, "MEL": 1.9, "BNE": 2.5, "ADL": 1.7
}

# Extra travel time added to each itinerary total travel time, editable.
EXTRA_TRAVEL_TIME = timedelta(hours=2.5)

class WithStops:

    def get_timezone(self, iata_code):
        return pytz.utc  # Avoiding API call limit errors

    def parse_duration(self, duration_str):
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', duration_str)
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return timedelta(hours=hours, minutes=minutes)

    def get_earliest_direct_flight(self, origin, destination, min_departure_time):
        try:
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=min_departure_time.strftime("%Y-%m-%d"),
                adults=1,
                currencyCode="USD",
                max=100
            )
            flights = response.data
            if not flights:
                return None

            valid_flights = []
            for flight in flights:
                segments = flight['itineraries'][0]['segments']
                # Skip flights that have more than one segment.
                if len(segments) > 1:
                    continue

                flight_details = segments[0]
                departure_time = datetime.strptime(flight_details['departure']['at'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.utc)
                cost = float(flight['price']['total'])

                if departure_time >= min_departure_time:
                    valid_flights.append((flight, cost))

            if not valid_flights:
                return None

            valid_flights.sort(key=lambda x: x[0]['itineraries'][0]['segments'][0]['departure']['at'])
            earliest_flight, cost = valid_flights[0]
            flight_details = earliest_flight['itineraries'][0]['segments'][0]

            departure_time = datetime.strptime(flight_details['departure']['at'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.utc)
            arrival_time = datetime.strptime(flight_details['arrival']['at'], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=pytz.utc)
            duration = self.parse_duration(flight_details['duration'])

            return {
                "airline": earliest_flight['validatingAirlineCodes'][0],
                "flight_number": flight_details['carrierCode'] + flight_details['number'],
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "origin": origin,
                "destination": destination,
                "duration": duration,
                "cost": cost
            }
        except ResponseError as error:
            print(f"Error fetching flights: {error}")
            return None

    def simulate_itinerary(self, start_origin, sequence, start_time):
        """
        Given a starting origin, a sequence (tuple) of destination IATA codes,
        and a starting time, simulate the itinerary.
        Returns itinerary details (or None if any flight in the sequence is missing).
        """
        origin = start_origin
        flights = []
        total_flight_duration = timedelta()
        total_layover_duration = timedelta()
        total_cost = 0.0
        previous_arrival_time = start_time
        previous_destination = origin

        for destination in sequence:
            flight = self.get_earliest_direct_flight(origin, destination, previous_arrival_time + timedelta(hours=buffer_hours[origin]))
            if flight:
                layover_duration = flight['departure_time'] - previous_arrival_time
                total_layover_duration += layover_duration
                flights.append({**flight, "layover": layover_duration, "layover_iata": previous_destination})
                total_flight_duration += flight['duration']
                total_cost += flight['cost']
                previous_arrival_time = flight['arrival_time']
                origin = destination
                previous_destination = destination
            else:
                return None  # Itinerary not possible for this sequence

        total_travel_time = total_flight_duration + total_layover_duration + EXTRA_TRAVEL_TIME
        return {
            "flights": flights,
            "total_flight_duration": total_flight_duration,
            "total_layover_duration": total_layover_duration,
            "total_travel_time": total_travel_time,
            "total_cost": total_cost
        }

def main():
    # Get user inputs
    start_origin = input("Enter origin airport code (e.g., JFK): ").upper().strip()
    departure_date = input("Enter departure date (YYYY-MM-DD): ").strip()
    # Note: This prompt text has been changed to indicate it's your arrival time in Chile.
    departure_time = input("Enter arrival time in Chile (HH:MM, 24-hour format): ").strip()

    try:
        current_time = datetime.strptime(f"{departure_date} {departure_time}", "%Y-%m-%d %H:%M")
        current_time = pytz.utc.localize(current_time)
    except ValueError:
        print("Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.")
        return

    # Prepare to iterate over all sequences: one destination from each continent.
    all_sequences = list(itertools.product(south_america_destinations, north_america_destinations, europe_destinations,
                                           africa_destinations, asia_destinations,
                                           australia_destinations))
    valid_itineraries = []
    sequence_count = 0
    with_stops = WithStops()

    # Check each full sequence
    for sequence in all_sequences:
        sequence_count += 1
        print(f"\nChecking sequence {sequence_count}: {sequence}")
        itinerary = with_stops.simulate_itinerary(start_origin, sequence, current_time)
        if itinerary:
            print("Itinerary found:")
            for flight in itinerary["flights"]:
                layover_str = f" | Layover in {flight['layover_iata']}: {flight['layover']}" if flight.get("layover") else ""
                print(f"{flight['origin']} -> {flight['destination']} | {flight['airline']} {flight['flight_number']} | "
                      f"Departure: {flight['departure_time']} | Arrival: {flight['arrival_time']} | Duration: {flight['duration']} | "
                      f"Cost: ${flight['cost']}{layover_str}")
            print(f"Total Flight Duration: {itinerary['total_flight_duration']}")
            print(f"Total Layover Duration: {itinerary['total_layover_duration']}")
            print(f"Total Travel Time: {itinerary['total_travel_time']}")
            print(f"Total Flight Cost: ${itinerary['total_cost']:.2f}")
            valid_itineraries.append((sequence, itinerary))
        else:
            print("No valid itinerary for this sequence.")

    # Determine the best itinerary (shortest total travel time) among valid ones.
    if valid_itineraries:
        best_sequence, best_itinerary = min(valid_itineraries, key=lambda x: x[1]["total_travel_time"])
        print("\nBest Itinerary Found:")
        print(f"Sequence: {best_sequence}")
        for flight in best_itinerary["flights"]:
            layover_str = f" | Layover in {flight['layover_iata']}: {flight['layover']}" if flight.get("layover") else ""
            print(f"{flight['origin']} -> {flight['destination']} | {flight['airline']} {flight['flight_number']} | "
                  f"Departure: {flight['departure_time']} | Arrival: {flight['arrival_time']} | Duration: {flight['duration']} | "
                  f"Cost: ${flight['cost']}{layover_str}")
        print(f"Total Flight Duration: {best_itinerary['total_flight_duration']}")
        print(f"Total Layover Duration: {best_itinerary['total_layover_duration']}")
        print(f"Total Travel Time: {best_itinerary['total_travel_time']}")
        print(f"Total Flight Cost: ${best_itinerary['total_cost']:.2f}")
    else:
        print("\nNo valid itineraries were found across all sequences.")

if __name__ == "__main__":
    main()
