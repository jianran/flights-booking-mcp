"""Flight search tools — Google Flights search + Duffel bookable offer search."""

import json
import logging
from typing import Optional
from mcp.server.fastmcp import FastMCP

from ..models import FlightSearch, MultiCityRequest, OfferDetails
from ..models.time_specs import TimeSpec
from ..api.google_flights import search_google_flights
from ..api.client import DuffelClient
from ..config import has_duffel

logger = logging.getLogger(__name__)

mcp = FastMCP("flights-booking-mcp")


def _build_slices(params: FlightSearch) -> list[dict]:
    """Build Duffel-format slice list from search params."""
    slices = []

    def _make_slice(origin: str, dest: str, date: str, dt: Optional[TimeSpec] = None, at: Optional[TimeSpec] = None) -> dict:
        s = {
            "origin": origin,
            "destination": dest,
            "departure_date": date,
            "departure_time": {"from": dt.from_time if dt else "00:00", "to": dt.to_time if dt else "23:59"},
            "arrival_time": {"from": at.from_time if at else "00:00", "to": at.to_time if at else "23:59"},
        }
        return s

    if params.type == "one_way":
        slices.append(_make_slice(params.origin, params.destination, params.departure_date,
                                  params.departure_time, params.arrival_time))
    elif params.type == "round_trip":
        if not params.return_date:
            raise ValueError("return_date required for round_trip")
        slices.append(_make_slice(params.origin, params.destination, params.departure_date,
                                  params.departure_time, params.arrival_time))
        slices.append(_make_slice(params.destination, params.origin, params.return_date,
                                  params.departure_time, params.arrival_time))
    elif params.type == "multi_city":
        slices.append(_make_slice(params.origin, params.destination, params.departure_date))
        if params.additional_stops:
            for stop in params.additional_stops:
                slices.append(_make_slice(stop["origin"], stop["destination"], stop["departure_date"]))

    return slices


def _format_offer_response(response: dict) -> dict:
    """Format Duffel offer response into a clean summary."""
    formatted = {
        "request_id": response.get("request_id", ""),
        "offers": [],
    }
    for offer in response.get("offers", [])[:20]:
        entry = {
            "offer_id": offer.get("id"),
            "price": {
                "amount": offer.get("total_amount"),
                "currency": offer.get("total_currency"),
            },
            "slices": [],
        }
        for s in offer.get("slices", []):
            segments = s.get("segments", [])
            if segments:
                seg_info = {
                    "origin": s["origin"]["iata_code"],
                    "destination": s["destination"]["iata_code"],
                    "departure": segments[0].get("departing_at"),
                    "arrival": segments[-1].get("arriving_at"),
                    "duration": s.get("duration"),
                    "carrier": segments[0].get("marketing_carrier", {}).get("name"),
                    "stops": len(segments) - 1,
                    "stop_label": "Non-stop" if len(segments) == 1 else f"{len(segments)-1} stop(s)",
                }
                entry["slices"].append(seg_info)
        formatted["offers"].append(entry)
    return formatted


@mcp.tool()
async def search_flights(
    type: str = "one_way",
    origin: str = "",
    destination: str = "",
    departure_date: str = "",
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "economy",
    max_stops: Optional[int] = None,
) -> str:
    """Search flights via Google Flights. Free, no API key required.
    
    Supports one-way, round-trip, and multi-city searches.
    Returns prices, airlines, schedules, and stop information.
    
    Args:
        type: Flight type — one_way, round_trip, or multi_city
        origin: IATA airport code (e.g., ICN, NRT, LHR)
        destination: IATA airport code
        departure_date: Date in YYYY-MM-DD format
        return_date: Return date for round_trip (optional)
        adults: Number of adult passengers (default: 1)
        cabin_class: economy, premium_economy, business, or first
        max_stops: Maximum number of stops (optional)
    """
    param = FlightSearch(
        type=type,
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        cabin_class=cabin_class,
        max_connections=max_stops,
    )

    logger.info(f"Searching Google Flights: {param.type} {param.origin}→{param.destination} on {param.departure_date}")

    try:
        results = search_google_flights(
            origin=param.origin,
            destination=param.destination,
            date=param.departure_date,
            return_date=param.return_date,
            adults=param.adults,
            cabin_class=param.cabin_class,
            max_stops=param.max_connections,
        )

        if not results:
            return json.dumps({
                "source": "google_flights",
                "message": "No flights found or service unavailable. Try search_bookable_offers for Duffel-powered results.",
                "flights": [],
            }, indent=2)

        return json.dumps({
            "source": "google_flights",
            "note": "Prices are for reference only. Use search_bookable_offers to get bookable offers.",
            "flights": results,
        }, indent=2)

    except Exception as e:
        logger.error(f"Flight search error: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def search_bookable_offers(
    type: str = "one_way",
    origin: str = "",
    destination: str = "",
    departure_date: str = "",
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "economy",
    max_connections: Optional[int] = None,
) -> str:
    """Search flights via Duffel API and get bookable offer_ids.
    
    Requires DUFFEL_API_TOKEN to be configured.
    The returned offer_ids can be used with book_flight to purchase.
    
    Args:
        type: Flight type — one_way, round_trip, or multi_city
        origin: IATA airport code
        destination: IATA airport code
        departure_date: Date in YYYY-MM-DD
        return_date: Return date for round_trip
        adults: Number of adult passengers
        cabin_class: economy, premium_economy, business, or first
        max_connections: Maximum connections (optional)
    """
    if not has_duffel():
        return json.dumps({
            "error": "DUFFEL_API_TOKEN not configured. Set it in .env or env vars.",
            "help": "Get a free test key at https://app.duffel.com",
        }, indent=2)

    param = FlightSearch(
        type=type,
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        cabin_class=cabin_class,
        max_connections=max_connections,
    )

    logger.info(f"Searching Duffel offers: {param.type} {param.origin}→{param.destination}")

    try:
        client = DuffelClient()
        slices = _build_slices(param)
        response = await client.create_offer_request(
            slices=slices,
            cabin_class=param.cabin_class,
            adult_count=param.adults,
            max_connections=param.max_connections,
            return_offers=True,
            supplier_timeout=15000,
        )
        formatted = _format_offer_response(response)
        formatted["source"] = "duffel"
        formatted["note"] = "These offers have valid offer_ids. Use book_flight(offer_id, passengers) to book."
        return json.dumps(formatted, indent=2)

    except Exception as e:
        logger.error(f"Duffel offer search error: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def get_offer_details(offer_id: str) -> str:
    """Get full details for a specific Duffel offer by offer_id.
    
    Returns detailed pricing, segment information, baggage policies, and
    fare conditions.
    
    Args:
        offer_id: Duffel offer ID (starts with off_)
    """
    if not has_duffel():
        return json.dumps({"error": "DUFFEL_API_TOKEN not configured"}, indent=2)

    try:
        client = DuffelClient()
        response = await client.get_offer(offer_id)
        return json.dumps(response, indent=2)
    except Exception as e:
        logger.error(f"Offer details error: {e}")
        return json.dumps({"error": str(e)}, indent=2)
