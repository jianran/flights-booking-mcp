"""Google Flights client using fast-flights library (v2 API)."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def search_google_flights(
    origin: str,
    destination: str,
    date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "economy",
    max_stops: Optional[int] = None,
) -> list[dict]:
    """Search flights via Google Flights data using fast-flights.

    Returns a list of flight results with prices, airlines, and schedules.
    No API key required.
    """
    try:
        from fast_flights import FlightData, Passengers, get_flights
    except ImportError:
        logger.warning("fast-flights not installed")
        return []

    seat_map = {
        "economy": "economy",
        "premium_economy": "premium-economy",
        "business": "business",
        "first": "first",
    }
    seat = seat_map.get(cabin_class, "economy")

    if return_date:
        trip_type = "round-trip"
        flight_data = [
            FlightData(date=date, from_airport=origin, to_airport=destination),
            FlightData(date=return_date, from_airport=destination, to_airport=origin),
        ]
    else:
        trip_type = "one-way"
        flight_data = [
            FlightData(
                date=date,
                from_airport=origin,
                to_airport=destination,
                max_stops=max_stops,
            )
        ]

    try:
        result = get_flights(
            flight_data=flight_data,
            trip=trip_type,
            passengers=Passengers(adults=adults),
            seat=seat,
            max_stops=max_stops,
        )

        flights = []
        if result and result.flights:
            for f in result.flights[:30]:
                flights.append({
                    "airline": f.name,
                    "departure": f.departure,
                    "arrival": f.arrival,
                    "duration": f.duration,
                    "stops": f.stops,
                    "price": f.price,
                    "is_best": getattr(f, "is_best", False),
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                })
            return flights

        return []

    except Exception as e:
        logger.error(f"Google Flights search error: {e}")
        return []
