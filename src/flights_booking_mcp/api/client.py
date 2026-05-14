"""Duffel API client — handles search, offers, and booking."""

import logging
import httpx
from typing import Any
from ..config import get_duffel_token

logger = logging.getLogger(__name__)

DUFFEL_BASE = "https://api.duffel.com/air"
DUFFEL_VERSION = "v2"


class DuffelClient:
    """Client for Duffel Air API — search offers and create orders."""

    def __init__(self):
        self._token = get_duffel_token()
        self._headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Duffel-Version": DUFFEL_VERSION,
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _check_token(self):
        if not self._token:
            raise ValueError(
                "DUFFEL_API_TOKEN not set. Get a free test key at https://app.duffel.com "
                "and set it in your .env file or DUFFEL_API_TOKEN environment variable."
            )

    async def create_offer_request(
        self,
        slices: list[dict],
        cabin_class: str = "economy",
        adult_count: int = 1,
        max_connections: int | None = None,
        return_offers: bool = True,
        supplier_timeout: int = 15000,
    ) -> dict:
        """Search flights via Duffel and get bookable offers with offer_ids."""
        self._check_token()

        request_data = {
            "data": {
                "slices": slices,
                "passengers": [{"type": "adult"} for _ in range(adult_count)],
                "cabin_class": cabin_class,
            }
        }
        if max_connections is not None:
            request_data["data"]["max_connections"] = max_connections

        params = {
            "return_offers": str(return_offers).lower(),
            "supplier_timeout": supplier_timeout,
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            resp = await client.post(
                f"{DUFFEL_BASE}/offer_requests",
                headers=self._headers,
                params=params,
                json=request_data,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "request_id": data["data"]["id"],
                "offers": data["data"].get("offers", []),
            }

    async def get_offer(self, offer_id: str) -> dict:
        """Get full details for a specific offer."""
        self._check_token()
        if not offer_id.startswith("off_"):
            raise ValueError("Invalid offer ID — must start with 'off_'")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DUFFEL_BASE}/offers/{offer_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def create_order(
        self,
        offer_id: str,
        passengers: list[dict],
        payment_type: str = "balance",
        payment_currency: str = "USD",
        payment_amount: str | None = None,
    ) -> dict:
        """Create a booking order.
        
        The passengers list must include the 'id' field from the offer's passenger.
        In test mode, use payment_type="balance" — no real charges occur.
        """
        self._check_token()

        if payment_amount is None:
            # Fetch offer to get the total amount
            offer_data = await self.get_offer(offer_id)
            offer = offer_data.get("data", {})
            payment_amount = offer.get("total_amount", "0.00")
            payment_currency = offer.get("total_currency", "USD")

        order_data = {
            "data": {
                "type": "instant",
                "selected_offers": [offer_id],
                "passengers": passengers,
                "payments": [
                    {
                        "type": payment_type,
                        "currency": payment_currency,
                        "amount": payment_amount,
                    }
                ],
            }
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(
                f"{DUFFEL_BASE}/orders",
                headers=self._headers,
                json=order_data,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_order(self, order_id: str) -> dict:
        """Get booking/order details."""
        self._check_token()
        if not order_id.startswith("ord_"):
            raise ValueError("Invalid order ID — must start with 'ord_'")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DUFFEL_BASE}/orders/{order_id}",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def list_orders(self, limit: int = 10) -> dict:
        """List recent orders."""
        self._check_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{DUFFEL_BASE}/orders",
                headers=self._headers,
                params={"limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    async def void_order(self, order_id: str) -> dict:
        """Void/cancel an order within the void window."""
        self._check_token()
        if not order_id.startswith("ord_"):
            raise ValueError("Invalid order ID — must start with 'ord_'")

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(
                f"{DUFFEL_BASE}/orders/{order_id}/actions/void",
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()
