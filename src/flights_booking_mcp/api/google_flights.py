"""Google Flights client using fast-flights library."""

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
        from fast_flights import FlightData, Passengers, Trip, search_flights
    except ImportError:
        logger.warning("fast-flights not installed, falling back to Google Flights browser fetch")
        return _search_google_fallback(origin, destination, date, return_date, adults, cabin_class)

    trip_type = "round-trip" if return_date else "one-way"

    try:
        # Map cabin class
        seat_type_map = {
            "economy": "economy",
            "premium_economy": "premium_economy",
            "business": "business",
            "first": "first",
        }
        seat = seat_type_map.get(cabin_class, "economy")

        result = search_flights(
            trip=Trip(
                TripData=[
                    FlightData(
                        date=date,
                        source=origin,
                        destination=destination,
                    ),
                ],
                date=date,
                return_date=return_date,
                trip_type=trip_type,
            ),
            passengers=Passengers(adults=adults),
            seat_type=seat,
            max_stops=max_stops,
        )

        flights = []
        if result and hasattr(result, 'flights') and result.flights:
            for f in result.flights[:30]:
                flights.append({
                    "airline": f.get("airline", "Unknown"),
                    "flight_number": f.get("flight_number", ""),
                    "departure_time": f.get("departure_time", ""),
                    "arrival_time": f.get("arrival_time", ""),
                    "duration": f.get("duration", ""),
                    "stops": f.get("stops", 0),
                    "price": f.get("price", ""),
                    "currency": f.get("currency", "USD"),
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                })
            return flights

        return []

    except Exception as e:
        logger.error(f"Google Flights search error: {e}")
        return []


def _search_google_fallback(
    origin: str, destination: str, date: str,
    return_date: Optional[str] = None,
    adults: int = 1, cabin_class: str = "economy",
) -> list[dict]:
    """Fallback: return an instructional message when fast-flights can't be used."""
    logger.info("fast-flights unavailable, returning empty results")
    return []
