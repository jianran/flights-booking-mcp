"""Flight booking tools — create orders, check status, void bookings."""

import json
import logging
from mcp.server.fastmcp import FastMCP

from ..api.client import DuffelClient
from ..config import has_duffel
from .profile import load_profile, save_profile, profile_exists, merge_with_profile

logger = logging.getLogger(__name__)

# Reuse the mcp instance from search
from .search import mcp


@mcp.tool()
async def save_travel_profile(
    given_name: str = "",
    family_name: str = "",
    title: str = "mr",
    gender: str = "m",
    born_on: str = "",
    phone_number: str = "",
    email: str = "",
) -> str:
    """Save your passenger details to a local profile file (~/.config/flights-booking-mcp/profile.json).
    
    Once saved, book_flight will auto-fill these values so you only need to provide
    the offer_id for future bookings.
    
    Args:
        given_name: First name (as on passport)
        family_name: Last name (as on passport)
        title: mr, ms, mrs, or mx
        gender: m or f
        born_on: Date of birth in YYYY-MM-DD (e.g., 1990-01-15)
        phone_number: Phone with country code (e.g., +821012345678)
        email: Email address
    """
    profile = {k: v for k, v in {
        "given_name": given_name,
        "family_name": family_name,
        "title": title,
        "gender": gender,
        "born_on": born_on,
        "phone_number": phone_number,
        "email": email,
    }.items() if v}

    if not profile:
        return json.dumps({"error": "At least one field must be provided"}, indent=2)

    save_profile(profile)
    return json.dumps({
        "status": "saved",
        "path": "~/.config/flights-booking-mcp/profile.json",
        "fields": list(profile.keys()),
    }, indent=2)


@mcp.tool()
async def show_travel_profile() -> str:
    """Show your saved travel profile (passenger details)."""
    profile = load_profile()
    if not profile:
        return json.dumps({"status": "no_profile",
                           "message": "No profile saved. Use save_travel_profile to create one."}, indent=2)
    return json.dumps({"status": "found", "profile": profile}, indent=2)


@mcp.tool()
async def book_flight(
    offer_id: str,
    given_name: str = "",
    family_name: str = "",
    title: str = "",
    gender: str = "",
    born_on: str = "",
    phone_number: str = "",
    email: str = "",
    payment_type: str = "balance",
    hold: bool = False,
) -> str:
    """Book a flight by creating a Duffel order.
    
    If you've saved your profile via save_travel_profile, most fields auto-fill.
    In test mode, payment_type="balance" means no real charges.
    Set hold=True to reserve without paying (30 min expiry, then confirm_booking).
    
    Args:
        offer_id: Duffel offer ID from search_bookable_offers (starts with off_)
        given_name: Passenger's first name (as on passport)
        family_name: Passenger's last name (as on passport)
        title: mr, ms, mrs, or mx
        gender: m or f
        born_on: Date of birth in YYYY-MM-DD (e.g., 1990-01-15)
        phone_number: Phone with country code (e.g., +821012345678)
        email: Email address
        payment_type: "balance" for test, "arc_bsp_cash" for live (default: balance)
        hold: If True, reserve without payment (use confirm_booking later). Default: False.
    """
    if not has_duffel():
        return json.dumps({
            "error": "DUFFEL_API_TOKEN not configured. Set it in .env or env vars.",
        }, indent=2)

    # Merge with saved profile
    kwargs = merge_with_profile({
        "given_name": given_name,
        "family_name": family_name,
        "title": title,
        "gender": gender,
        "born_on": born_on,
        "phone_number": phone_number,
        "email": email,
    })

    missing = [k for k in ["given_name", "family_name", "born_on", "phone_number", "email"]
               if not kwargs.get(k)]
    if missing:
        msg = (f"Missing required fields: {', '.join(missing)}. "
               "Provide them directly or save via save_travel_profile first.")
        return json.dumps({"error": msg}, indent=2)

    logger.info(f"Booking offer {offer_id} (hold={hold})")

    try:
        client = DuffelClient()

        # Fetch offer to get passenger_id and price
        offer_data = await client.get_offer(offer_id)
        offer = offer_data.get("data", {})

        if not offer.get("passengers"):
            return json.dumps({"error": "No passenger info found in offer"}, indent=2)

        passenger_id = offer["passengers"][0]["id"]
        total_amount = offer.get("total_amount", "0.00")
        total_currency = offer.get("total_currency", "USD")

        passengers = [{
            "id": passenger_id,
            "title": kwargs["title"] or "mr",
            "given_name": kwargs["given_name"],
            "family_name": kwargs["family_name"],
            "gender": kwargs["gender"] or "m",
            "born_on": kwargs["born_on"],
            "phone_number": kwargs["phone_number"],
            "email": kwargs["email"],
        }]

        if hold:
            # Duffel hold flow: create order with payment_type="hold", then confirm later
            result = await client.create_order(
                offer_id=offer_id,
                passengers=passengers,
                payment_type="hold",
                payment_currency=total_currency,
                payment_amount=total_amount,
            )
        else:
            result = await client.create_order(
                offer_id=offer_id,
                passengers=passengers,
                payment_type=payment_type,
                payment_currency=total_currency,
                payment_amount=total_amount,
            )

        order = result.get("data", {})
        is_hold = order.get("type") == "hold" or hold

        response = {
            "status": "held" if is_hold else "confirmed",
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
            "live_mode": order.get("live_mode", False),
        }

        if is_hold:
            response["next_step"] = "Call confirm_booking(order_id) to confirm and pay."

        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Booking error: {e}")
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def confirm_booking(order_id: str, payment_type: str = "balance") -> str:
    """Confirm a held booking and process payment.
    
    Use this after book_flight(..., hold=True). The offer is reserved for ~30 min.
    
    Args:
        order_id: Duffel order ID from book_flight (starts with ord_)
        payment_type: "balance" for test mode, "arc_bsp_cash" for live (default: balance)
    """
    if not has_duffel():
        return json.dumps({"error": "DUFFEL_API_TOKEN not configured"}, indent=2)

    logger.info(f"Confirming order {order_id}")

    try:
        client = DuffelClient()

        # Get the order to find the amount
        order_data = await client.get_order(order_id)
        order = order_data.get("data", {})

        if order.get("type") != "hold":
            return json.dumps({
                "info": "Order is not in hold status. Current type: " + order.get("type", "unknown"),
                "order_id": order_id,
            }, indent=2)

        total_amount = order.get("total_amount", "0.00")
        total_currency = order.get("total_currency", "USD")

        # Pay the held order via Duffel pay endpoint
        import httpx
        from ..config import get_duffel_token

        token = get_duffel_token()
        headers = {
            "Accept": "application/json",
            "Duffel-Version": "v2",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "data": {
                "payments": [{
                    "type": payment_type,
                    "currency": total_currency,
                    "amount": total_amount,
                }]
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as hc:
            resp = await hc.post(
                f"https://api.duffel.com/air/orders/{order_id}/actions/pay",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            result = resp.json()

        updated = result.get("data", {})
        return json.dumps({
            "status": "confirmed",
            "order_id": updated.get("id"),
            "booking_reference": updated.get("booking_reference"),
            "total_amount": updated.get("total_amount"),
            "total_currency": updated.get("total_currency"),
            "payment_status": updated.get("payment_status"),
            "live_mode": updated.get("live_mode", False),
        }, indent=2)

    except Exception as e:
        logger.error(f"Confirm booking error: {e}")
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
