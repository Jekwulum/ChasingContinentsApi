from flask import Flask, jsonify, request
from datetime import datetime
from amadeus_client import AmadeusClient

app = Flask(__name__)
amadeus_client = AmadeusClient()


@app.route("/flights", methods=["GET"])
def get_flights():
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    departure_date = request.args.get("departure_date")
    if not all([origin, destination, departure_date]):
        return (
            jsonify(
                {
                    "message": "ERROR: Please provide origin, destination, and departure_date."
                }
            ),
            400,
        )

    departure_date = datetime.strptime(departure_date, "%Y-%m-%d").date()
    flights_data = amadeus_client.fetch_flights(origin, destination, departure_date)

    if flights_data:
        carriers = flights_data["dictionaries"]["carriers"]
        flights = [
            amadeus_client.process_flight(flight, carriers)
            for flight in flights_data["data"]
        ]
        return jsonify({"data": flights})
    else:
        return jsonify({"message": "No flights found."}), 404


@app.route("/airports", methods=["GET"])
def get_airports():
    keyword = request.args.get("keyword")
    if not keyword:
        return jsonify({"message": "ERROR: Please provide a keyword."}), 400

    airports_data = amadeus_client.fetch_airports(keyword)
    if airports_data:
        return jsonify(airports_data)
    else:
        return jsonify({"message": "No airports found."}), 404


if __name__ == "__main__":
    app.run(debug=True)
