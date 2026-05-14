"""Flight booking tools — create orders, check status, void bookings."""

import json
import logging
from mcp.server.fastmcp import FastMCP

from ..api.client import DuffelClient
from ..config import has_duffel

logger = logging.getLogger(__name__)

# Reuse the mcp instance from search
from .search import mcp


@mcp.tool()
async def book_flight(
    offer_id: str,
    given_name: str,
    family_name: str,
    title: str = "mr",
    gender: str = "m",
    born_on: str = "",
    phone_number: str = "",
    email: str = "",
    payment_type: str = "balance",
) -> str:
    """Book a flight by creating a Duffel order.
    
    Requires DUFFEL_API_TOKEN. In test mode (default), use payment_type="balance"
    — no real charges occur.
    
    Args:
        offer_id: Duffel offer ID from search_bookable_offers (starts with off_)
        given_name: Passenger's first name (as on passport)
        family_name: Passenger's last name (as on passport)
        title: mr, ms, mrs, or mx (default: mr)
        gender: m or f (default: m)
        born_on: Date of birth in YYYY-MM-DD format (e.g., 1990-01-15)
        phone_number: Phone with country code (e.g., +821012345678)
        email: Email address
        payment_type: "balance" for test mode, "arc_bsp_cash" for live (default: balance)
    """
    if not has_duffel():
        return json.dumps({
            "error": "DUFFEL_API_TOKEN not configured. Set it in .env or env vars.",
        }, indent=2)

    logger.info(f"Booking offer {offer_id}")

    try:
        client = DuffelClient()

        # Fetch offer to get passenger_id and price
        offer_data = await client.get_offer(offer_id)
        offer = offer_data.get("data", {})

        if not offer.get("passengers"):
            return json.dumps({"error": "No passenger info found in offer"}, indent=2)

        # Get the passenger ID from the offer
        passenger_id = offer["passengers"][0]["id"]
        total_amount = offer.get("total_amount", "0.00")
        total_currency = offer.get("total_currency", "USD")

        passengers = [{
            "id": passenger_id,
            "title": title,
            "given_name": given_name,
            "family_name": family_name,
            "gender": gender,
            "born_on": born_on,
            "phone_number": phone_number,
            "email": email,
        }]

        result = await client.create_order(
            offer_id=offer_id,
            passengers=passengers,
            payment_type=payment_type,
            payment_currency=total_currency,
            payment_amount=total_amount,
        )

        order = result.get("data", {})
        return json.dumps({
            "status": "success",
            "order_id": order.get("id"),
            "booking_reference": order.get("booking_reference"),
            "total_amount": order.get("total_amount"),
            "total_currency": order.get("total_currency"),
            "passengers": [
                {"id": p.get("id"), "name": f"{p.get('given_name', '')} {p.get('family_name', '')}"}
                for p in order.get("passengers", [])
            ],
            "slices": [
                {
                    "origin": s.get("origin", {}).get("iata_code"),
                    "destination": s.get("destination", {}).get("iata_code"),
                }
                for s in order.get("slices", [])
            ],
            "payment_status": order.get("payment_status"),
            "live_mode": order.get("live_mode", False),
        }, indent=2)

    except Exception as e:
        logger.error(f"Booking error: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def get_booking_status(order_id: str) -> str:
    """Check the status of a booked order.
    
    Returns booking reference, passenger details, slices, payment status.
    
    Args:
        order_id: Duffel order ID (starts with ord_)
    """
    if not has_duffel():
        return json.dumps({"error": "DUFFEL_API_TOKEN not configured"}, indent=2)

    try:
        client = DuffelClient()
        result = await client.get_order(order_id)
        order = result.get("data", {})

        return json.dumps({
            "order_id": order.get("id"),
            "booking_reference": order.get("booking_reference"),
            "status": order.get("type"),
            "total_amount": order.get("total_amount"),
            "total_currency": order.get("total_currency"),
            "live_mode": order.get("live_mode", False),
            "payment_status": order.get("payment_status", {}),
            "void_window_ends_at": order.get("void_window_ends_at"),
            "passengers": [
                {
                    "id": p.get("id"),
                    "name": f"{p.get('given_name', '')} {p.get('family_name', '')}",
                    "type": p.get("type"),
                }
                for p in order.get("passengers", [])
            ],
            "slices": [
                {
                    "origin": s.get("origin", {}).get("iata_code"),
                    "destination": s.get("destination", {}).get("iata_code"),
                    "departure": s.get("segments", [{}])[0].get("departing_at") if s.get("segments") else None,
                    "arrival": s.get("segments", [{}])[-1].get("arriving_at") if s.get("segments") else None,
                }
                for s in order.get("slices", [])
            ],
        }, indent=2)

    except Exception as e:
        logger.error(f"Status check error: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def list_bookings(limit: int = 10) -> str:
    """List recent flight bookings.
    
    Args:
        limit: Maximum number of bookings to return (default: 10)
    """
    if not has_duffel():
        return json.dumps({"error": "DUFFEL_API_TOKEN not configured"}, indent=2)

    try:
        client = DuffelClient()
        result = await client.list_orders(limit=limit)
        orders = result.get("data", [])

        return json.dumps({
            "count": len(orders),
            "bookings": [
                {
                    "order_id": o.get("id"),
                    "booking_reference": o.get("booking_reference"),
                    "total_amount": o.get("total_amount"),
                    "total_currency": o.get("total_currency"),
                    "type": o.get("type"),
                    "created_at": o.get("created_at"),
                    "live_mode": o.get("live_mode", False),
                    "slices": [
                        f"{s.get('origin', {}).get('iata_code', '?')} → {s.get('destination', {}).get('iata_code', '?')}"
                        for s in o.get("slices", [])
                    ],
                }
                for o in orders
            ],
        }, indent=2)

    except Exception as e:
        logger.error(f"List bookings error: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def void_booking(order_id: str) -> str:
    """Void/cancel a booking within the void window (typically 24h).
    
    Args:
        order_id: Duffel order ID (starts with ord_)
    """
    if not has_duffel():
        return json.dumps({"error": "DUFFEL_API_TOKEN not configured"}, indent=2)

    logger.info(f"Voiding order {order_id}")

    try:
        client = DuffelClient()
        result = await client.void_order(order_id)
        order = result.get("data", {})

        return json.dumps({
            "status": "voided",
            "order_id": order.get("id"),
            "booking_reference": order.get("booking_reference"),
            "total_amount": order.get("total_amount"),
            "total_currency": order.get("total_currency"),
            "voided_at": order.get("voided_at"),
            "live_mode": order.get("live_mode", False),
        }, indent=2)

    except Exception as e:
        logger.error(f"Void booking error: {e}")
        return json.dumps({"error": str(e)}, indent=2)
