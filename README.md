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
| `book_flight` | Book a flight by Duffel `offer_id` + passenger details |
| `get_booking_status` | Check booking status / PNR |
| `void_booking` | Cancel a booking within the void window |

## Booking flow

```
1. search_flights(ICN → NRT, July 1)     ← free Google Flights, browse prices
2. search_bookable_offers(ICN → NRT, July 1)  ← get bookable offer_ids from Duffel
3. book_flight(off_xxx, passengers)       ← creates order, returns booking ref
4. get_booking_status(ord_xxx)            ← check PNR, ticket status
```

## Duffel setup

1. Sign up at [app.duffel.com](https://app.duffel.com) (free)
2. Use your auto-generated test key (`duffel_test_...`) — works for search and test bookings
3. For real bookings: complete verification + add payment info → get a live key

In test mode, use `"type": "balance"` for payments — no real charges.

## License

MIT
