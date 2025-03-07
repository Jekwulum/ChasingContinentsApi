import requests
from config import AMADEUS_API_KEY, AMADEUS_API_SECRET, AMADEUS_BASE_URL


class AmadeusClient:
    def __init__(self):
        """Initialize the Amadeus client."""
        if not all([AMADEUS_API_KEY, AMADEUS_API_SECRET]):
            raise ValueError(
                "❌ ERROR: AMADEUS_API_KEY and AMADEUS_API_SECRET must be set in the .env file."
            )

        self.base_url = AMADEUS_BASE_URL
        self.api_key = AMADEUS_API_KEY
        self.api_secret = AMADEUS_API_SECRET
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        """Get the access token from the Amadeus API."""
        url = f"{self.base_url}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret,
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json().get("access_token")

    def fetch_flights(self, origin, destination, departure_date):
        """
        Fetch flights from the Amadeus API.
        :param origin: The origin location code. e.g. "LAX".
        :param destination: The destination location code. e.g. "JFK".
        :param departure_date: The departure date. e.g. "2022-12-01".
        """
        url = f"{self.base_url}/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": 1,
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def fetch_airports(self, keyword):
        """
        Fetch airports from the Amadeus API.
        :param keyword: The keyword to search for airports. e.g. "New York".
        """
        url = f"{self.base_url}/v1/reference-data/locations"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {"keyword": keyword, "subType": "CITY,AIRPORT"}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def process_flight(self, flight, carriers):
        """Process a single flight entry."""
        processed_flight = {
            "amount": flight["price"]["total"],
            "currency": flight["price"]["currency"],
            "itineraries": [
                {
                    "duration": itinerary["duration"],
                    "segments": [
                        {
                            "airline": {
                                "code": segment["carrierCode"],
                                "airline_name": carriers.get(
                                    segment["carrierCode"], "Unknown Airline"
                                ),
                            },
                            "arrival": segment["arrival"],
                            "departure": segment["departure"],
                        }
                        for segment in itinerary["segments"]
                    ],
                }
                for itinerary in flight["itineraries"]
            ],
        }
        return processed_flight
