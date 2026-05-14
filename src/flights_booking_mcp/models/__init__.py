"""Pydantic models for flight search."""

from pydantic import BaseModel, Field
from typing import List, Optional
from .time_specs import TimeSpec


class FlightSearch(BaseModel):
    """Parameters for searching flights."""
    type: str = Field(description="flight type: one_way, round_trip, or multi_city")
    origin: str = Field(description="origin IATA airport code, e.g. ICN")
    destination: str = Field(description="destination IATA airport code, e.g. NRT")
    departure_date: str = Field(description="departure date in YYYY-MM-DD")
    return_date: Optional[str] = Field(None, description="return date in YYYY-MM-DD (round_trip only)")
    adults: int = Field(1, description="number of adult passengers")
    cabin_class: str = Field("economy", description="cabin class: economy, premium_economy, business, first")
    max_connections: Optional[int] = Field(None, description="maximum number of connections")
    departure_time: Optional[TimeSpec] = Field(None, description="preferred departure time range")
    arrival_time: Optional[TimeSpec] = Field(None, description="preferred arrival time range")
    additional_stops: Optional[List[dict]] = Field(None, description="additional stops for multi_city flights")


class MultiCitySegment(BaseModel):
    """A single segment in a multi-city search."""
    origin: str = Field(description="origin IATA code")
    destination: str = Field(description="destination IATA code")
    departure_date: str = Field(description="departure date in YYYY-MM-DD")


class MultiCityRequest(BaseModel):
    """Parameters for multi-city flight search."""
    segments: List[MultiCitySegment]
    adults: int = Field(1, description="number of adult passengers")
    cabin_class: str = Field("economy", description="cabin class")
    max_connections: Optional[int] = Field(None, description="maximum connections")


class OfferDetails(BaseModel):
    """Get details for a specific offer."""
    offer_id: str = Field(description="Duffel offer ID to get details for")
