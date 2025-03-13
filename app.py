import pytz
import os
import itertools
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
from withstops import WithStops
from directonly import DirectFlight

south_america_destinations = ["SCL"]
north_america_destinations = ["MIA", "PTY", "LAX", "SFO", "SAN", "TIJ"]
europe_destinations = ["MAD", "LIS", "BCN", "ORY", "CMN"]
africa_destinations = ["CMN", "CAI"]
asia_destinations = ["DOH", "DXB", "KUL"]
australia_destinations = ["PER"]

load_dotenv()
app = Flask(__name__)
CORS(app)

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "UP"})

@app.route("/api/flights", methods=["GET"])
def fetch_flights():
    start_origin = request.args.get("start_origin")
    departure_date = request.args.get("departure_date")
    departure_time = request.args.get("departure_time")
    flight_type = request.args.get("flight_type", "direct") # direct or stops

    try:
        current_time = datetime.strptime(
            f"{departure_date} {departure_time}", "%Y-%m-%d %H:%M"
        )
        current_time = pytz.utc.localize(current_time)
    except ValueError:
        return jsonify(
            {
                "status": "FAILED",
                "message": "Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for time.",
            }
        )

    all_sequences = list(
        itertools.product(
            south_america_destinations,
            north_america_destinations,
            europe_destinations,
            africa_destinations,
            asia_destinations,
            australia_destinations,
        )
    )
    valid_itineraries = []
    sequence_count = 0

    flight_instance = None

    if flight_type == "direct":
        flight_instance = DirectFlight()
    else:
        flight_instance = WithStops()

    # Check each full sequence
    for sequence in all_sequences:
        sequence_count += 1
        print(f"\nChecking sequence {sequence_count}: {sequence}")
        itinerary = flight_instance.simulate_itinerary(
            start_origin, sequence, current_time
        )
        if itinerary:
            print("Itinerary found:")
            for flight in itinerary["flights"]:
                layover_str = (
                    f" | Layover in {flight['layover_iata']}: {flight['layover']}"
                    if flight.get("layover")
                    else ""
                )
                print(
                    f"{flight['origin']} -> {flight['destination']} | {flight['airline']} {flight['flight_number']} | "
                    f"Departure: {flight['departure_time']} | Arrival: {flight['arrival_time']} | Duration: {flight['duration']} | "
                    f"Cost: ${flight['cost']}{layover_str}"
                )
            print(f"Total Flight Duration: {itinerary['total_flight_duration']}")
            print(f"Total Layover Duration: {itinerary['total_layover_duration']}")
            print(f"Total Travel Time: {itinerary['total_travel_time']}")
            print(f"Total Flight Cost: ${itinerary['total_cost']:.2f}")
            valid_itineraries.append((sequence, itinerary))
        else:
            print("No valid itinerary for this sequence.")

    # Determine the best itinerary (shortest total travel time) among valid ones.
    if valid_itineraries:
        best_sequence, best_itinerary = min(
            valid_itineraries, key=lambda x: x[1]["total_travel_time"]
        )

        print(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
        print({best_sequence, best_itinerary})

        return jsonify({"status": "SUCCESS", "data": {best_sequence, best_itinerary}})
    else:
        return jsonify(
            {
                "status": "FAILED",
                "message": "No valid itineraries were found across all sequences.",
            }
        )


if __name__ == "__main__":
    app.run(debug=True)
