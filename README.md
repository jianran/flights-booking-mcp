# flights-booking-mcp ✈️

**Hybrid MCP server: Google Flights search + Duffel flight booking.**

Search flights with **zero setup** (no API keys needed), then book directly through your AI assistant.

## Why this exists

| What | How | Cost |
|---|---|---|
| **Search** | Google Flights via `fast-flights` | Free, no account needed |
| **Book** | Duffel API `create_order` | Free in test mode, real bookings need live key |

Existing flight MCPs are either **search-only** or **require a Duffel key just to search**. This combines the best of both: free Google Flights search + Duffel's booking pipeline.

## Quick start

### Install

```bash
pip install flights-booking-mcp
# or: uv add flights-booking-mcp
```

### Configure

Add to your MCP client config:

```json
{
  "mcpServers": {
    "flights-booking": {
      "command": "uvx",
      "args": ["flights-booking-mcp"]
    }
  }
}
```

For booking, add your Duffel API key to `.env` or pass it as an env var:

```json
{
  "mcpServers": {
    "flights-booking": {
      "command": "uvx",
      "args": ["flights-booking-mcp"],
      "env": {
        "DUFFEL_API_TOKEN": "duffel_test_..."
      }
    }
  }
}
```

### Run from source

```bash
git clone https://github.com/jianran/flights-booking-mcp.git
cd flights-booking-mcp
cp .env.example .env
# Edit .env with your keys
uv run flights-booking-mcp
```

## Tools

### Search (no API key required)

| Tool | Description |
|---|---|
| `search_flights` | One-way, round-trip, or multi-city via Google Flights |
| `get_offer_details` | Get full details on a specific offer |

### Book (requires Duffel API key)

| Tool | Description |
|---|---|
| `search_bookable_offers` | Search flights and get Duffel-compatible `offer_id`s |
| `book_flight` | Book a flight — instant or hold, with or without saved profile |
| `confirm_booking` | Confirm a held booking (reserved via `book_flight(hold=True)`) |
| `get_booking_status` | Check booking status / PNR |
| `list_bookings` | View recent booking history |
| `void_booking` | Cancel a booking within the void window |

### Profile (save passenger details once)

| Tool | Description |
|---|---|
| `save_travel_profile` | Save your passenger details locally (name, DOB, etc.) |
| `show_travel_profile` | View your saved profile |

## Booking flows

### Instant (default) — book and pay in one step

```
1. save_travel_profile(given_name="Stefan", ...)     ← save once
2. search_flights(ICN → NRT, July 1)                 ← browse free Google Flights
3. search_bookable_offers(ICN → NRT, July 1)         ← get bookable offer_ids
4. book_flight(off_xxx)                              ← auto-fills from profile
```

### Hold + Confirm — two-step with confirmation gate

```
1. book_flight(off_xxx, hold=True)              ← reserves without paying (~30 min)
2. confirm_booking(ord_xxx)                     ← confirm and pay
```

The confirmation step is a manual gate — no money moves until you call `confirm_booking`. Perfect for when you want to review before committing.

### Save your profile

```python
save_travel_profile(
    given_name="Stefan",
    family_name="Test",
    title="mr",
    gender="m",
    born_on="1990-01-15",
    phone_number="+821012345678",
    email="stefan@example.com"
)
```

After this, `book_flight` only needs the `offer_id` — everything else auto-fills.

## Duffel setup

1. Sign up at [app.duffel.com](https://app.duffel.com) (free)
2. Use your auto-generated test key (`duffel_test_...`) — works for search and test bookings
3. For real bookings: complete verification + add payment info → get a live key

In test mode, `payment_type="balance"` prevents any real charges.

## License

MIT
