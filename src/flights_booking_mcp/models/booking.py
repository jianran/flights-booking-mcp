"""Pydantic models for flight booking."""

from pydantic import BaseModel, Field
from typing import List, Optional


class PassengerInfo(BaseModel):
    """Passenger details required for booking."""
    title: str = Field(description="mr, ms, mrs, or mx")
    given_name: str = Field(description="first name as on passport")
    family_name: str = Field(description="last name as on passport")
    gender: str = Field(description="m or f")
    born_on: str = Field(description="date of birth in YYYY-MM-DD")
    phone_number: str = Field(description="phone number with country code, e.g. +821012345678")
    email: str = Field(description="email address")


class PaymentInfo(BaseModel):
    """Payment details for booking."""
    type: str = Field("balance", description="payment type: balance (test) or arc_bsp_cash")
    currency: str = Field(description="currency code, e.g. USD")
    amount: str = Field(description="amount to charge, e.g. 299.50")


class BookFlightRequest(BaseModel):
    """Parameters to book a flight."""
    offer_id: str = Field(description="Duffel offer ID (starts with off_)")
    passengers: List[PassengerInfo] = Field(description="list of passengers")
    payment_currency: str = Field("USD", description="payment currency code")
    payment_type: str = Field("balance", description="payment type: balance for test, arc_bsp_cash for live")


class BookingStatusRequest(BaseModel):
    """Parameters to check booking status."""
    order_id: str = Field(description="Duffel order ID to check")


class VoidBookingRequest(BaseModel):
    """Parameters to void a booking."""
    order_id: str = Field(description="Duffel order ID to void")
