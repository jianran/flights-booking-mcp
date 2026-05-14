"""Flight booking tools — create orders, check status, void bookings."""

import json
import logging
from typing import List
from mcp.server.fastmcp import FastMCP

from ..api.client import DuffelClient
from ..config import has_duffel

logger = logging.getLogger(__name__)

# Reuse the mcp instance from search
from .search import mcp


@mcp.tool()
async def book_flight(
    offer_id: str,
    passengers: list[dict],
    payment_type: str = "balance",
    payment_currency: str = "USD",
) -> str:
    """Book a flight by creating a Duffel order.
    
    Requires DUFFEL_API_TOKEN. In test mode, use payment_type="balance"
    — no real charges occur.
    
    Args:
        offer_id: Duffel offer ID from search_bookable_offers (starts with off_)
        passengers: List of passenger dicts, each with:
            - title: mr/ms/mrs/mx
            - given_name: first name
            - family_name: last name
            - gender: m or f
            - born_on: YYYY-MM-DD
            - phone_number: +821012345678
            - email: email address
        payment_type: "balance" for test mode, "arc_bsp_cash" for live
        payment_currency: ISO currency code (default: USD)
    """
    if not has_duffel():
        return json.dumps({
            "error": "DUFFEL_API_TOKEN not configured. Set it in .env or env vars.",
        }, indent=2)

    logger.info(f"Booking offer {offer_id} for {len(passengers)} passenger(s)")

    try:
        client = DuffelClient()

        # Validate and format passengers
        formatted_passengers = []
        for p in passengers:
            formatted_passengers.append({
                "title": p["title"],
                "given_name": p["given_name"],
                "family_name": p["family_name"],
                "gender": p["gender"],
                "born_on": p["born_on"],
                "phone_number": p["phone_number"],
                "email": p["email"],
            })

        result = await client.create_order(
            offer_id=offer_id,
            passengers=formatted_passengers,
            payment_type=payment_type,
            payment_currency=payment_currency,
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
