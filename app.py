import pytz
import os
import itertools
import json
import datetime
# import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime as dt
from withstops import WithStops
from directonly import DirectFlight
from email_flights_data import EmailFlightData

south_america_destinations = ["SCL"]
north_america_destinations = ["MIA", "PTY", "LAX", "SFO", "SAN", "TIJ"]
europe_destinations = ["MAD", "LIS", "BCN", "ORY", "CMN"]
africa_destinations = ["CMN", "CAI"]
asia_destinations = ["DOH", "DXB", "KUL"]
australia_destinations = ["PER"]

load_dotenv()
app = Flask(__name__)
CORS(app)


def serialize_datetime(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.timedelta):
        return str(obj)
    raise TypeError(f"Type not serializable: {obj}")


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "UP"})


@app.route("/api/flights", methods=["GET"])
def fetch_flights():
    start_origin = request.args.get("start_origin")
    departure_date = request.args.get("departure_date")
    departure_time = request.args.get("departure_time")
    flight_type = request.args.get("flight_type", "direct")  # direct or stops
    email = request.args.get("email", None)

    try:
        current_time = dt.strptime(
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
        if sequence_count == 60:
            break
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

        print(
            "::::::::::::::::::::::::::::::best sequence:::::::::::::::::::::::::::::::::::::::"
        )
        print(best_sequence)

        print(
            "::::::::::::::::::::::::::::::best itinerary:::::::::::::::::::::::::::::::::::::::"
        )
        print(best_itinerary)

        best_itinerary = json.dumps(best_itinerary, default=serialize_datetime)

        if email:
            email_data = EmailFlightData()
            subject = "Flight Itinerary"
            email_content = email_data.format_email_content(best_sequence, best_itinerary)
            email_data.send_mail(email, subject, email_content)

        return jsonify(
            {
                "status": "SUCCESS",
                "data": {"best_sequence": best_sequence, "best_itinerary": best_itinerary},
            }
        )
    else:
        return jsonify(
            {
                "status": "FAILED",
                "message": "No valid itineraries were found across all sequences.",
            }
        )
    

@app.route("/api/tests", methods=["GET"])
def test():
    best_itinerary = {
        'flights': [
            {
                'airline': 'LA',
                'flight_number': 'LA896',
                'departure_time': datetime.datetime(2025, 3, 15, 20, 20, tzinfo=datetime.timezone.utc),
                'arrival_time': datetime.datetime(2025, 3, 15, 23, 45, tzinfo=datetime.timezone.utc),
                'origin': 'PUQ',
                'destination': 'SCL',
                'duration': datetime.timedelta(seconds=12300),
                'cost': 79.1,
                'layover': datetime.timedelta(seconds=10200),
                'layover_iata': 'PUQ'
            },
            {
                'airline': 'LA',
                'flight_number': 'LA504',
                'departure_time': datetime.datetime(2025, 3, 16, 9, 25, tzinfo=datetime.timezone.utc),
                'arrival_time': datetime.datetime(2025, 3, 16, 16, 55, tzinfo=datetime.timezone.utc),
                'origin': 'SCL',
                'destination': 'MIA',
                'duration': datetime.timedelta(seconds=30600),
                'cost': 845.81,
                'layover': datetime.timedelta(seconds=34800),
                'layover_iata': 'SCL'
            },
            {
                'airline': 'UX',
                'flight_number': 'UX98',
                'departure_time': datetime.datetime(2025, 3, 16, 22, 45, tzinfo=datetime.timezone.utc),
                'arrival_time': datetime.datetime(2025, 3, 17, 12, 5, tzinfo=datetime.timezone.utc),
                'origin': 'MIA',
                'destination': 'MAD',
                'duration': datetime.timedelta(seconds=30000),
                'cost': 414.0,
                'layover': datetime.timedelta(seconds=21000),
                'layover_iata': 'MIA'
            },
            {
                'airline': 'MS',
                'flight_number': 'MS754',
                'departure_time': datetime.datetime(2025, 3, 17, 14, 50, tzinfo=datetime.timezone.utc),
                'arrival_time': datetime.datetime(2025, 3, 17, 20, 35, tzinfo=datetime.timezone.utc),
                'origin': 'MAD',
                'destination': 'CAI',
                'duration': datetime.timedelta(seconds=17100),
                'cost': 194.89,
                'layover': datetime.timedelta(seconds=9900),
                'layover_iata': 'MAD'
            },
            {
                'airline': 'MS',
                'flight_number': 'MS910',
                'departure_time': datetime.datetime(2025, 3, 17, 22, 35, tzinfo=datetime.timezone.utc),
                'arrival_time': datetime.datetime(2025, 3, 18, 3, 45, tzinfo=datetime.timezone.utc),
                'origin': 'CAI',
                'destination': 'DXB',
                'duration': datetime.timedelta(seconds=11400),
                'cost': 234.99,
                'layover': datetime.timedelta(seconds=7200),
                'layover_iata': 'CAI'
            },
            {
                'airline': 'EK',
                'flight_number': 'EK424',
                'departure_time': datetime.datetime(2025, 3, 18, 9, 15, tzinfo=datetime.timezone.utc),
                'arrival_time': datetime.datetime(2025, 3, 19, 0, 10, tzinfo=datetime.timezone.utc),
                'origin': 'DXB',
                'destination': 'PER',
                'duration': datetime.timedelta(seconds=39300),
                'cost': 1185.4,
                'layover': datetime.timedelta(seconds=19800),
                'layover_iata': 'DXB'
            }
        ],
        'total_flight_duration': datetime.timedelta(days=1, seconds=54300),
        'total_layover_duration': datetime.timedelta(days=1, seconds=16500),
        'total_travel_time': datetime.timedelta(days=2, seconds=79800),
        'total_cost': 2954.1899999999996
    }
    best_itinerary = json.dumps(best_itinerary, default=serialize_datetime)
    best_sequence = ["SCL", "MIA", "MAD", "CAI", "DOH", "PER"]
    email = "charlesnwoye2@gmail.com"
    subject = "Flight Itinerary"
    email_data = EmailFlightData()
    email_content = email_data.format_email_content(best_sequence, best_itinerary)
    email_data.send_mail(email, subject, email_content)
    return jsonify({"status": "SUCCESS", "data": {"best_itinerary": best_itinerary, "best_sequence": best_sequence}})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    # logging.basicConfig(level=logging.DEBUG)
