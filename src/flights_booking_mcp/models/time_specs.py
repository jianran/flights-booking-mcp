"""Time specification model."""

from pydantic import BaseModel, Field


class TimeSpec(BaseModel):
    """Time range specification."""
    from_time: str = Field(description="start time in HH:MM format")
    to_time: str = Field(description="end time in HH:MM format")
