# Travel Planner Agent

> A multi-agent travel planning system built with Google ADK that coordinates flight/hotel search, booking simulation, and itinerary generation with Model Context Protocol (MCP) payment tools.

[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4?logo=google)](https://github.com/google/generative-ai-dart)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?logo=postgresql)](https://www.postgresql.org/)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [Agent Hierarchy](#agent-hierarchy)
  - [Workflow Phases](#workflow-phases)
  - [User Confirmation Pattern](#user-confirmation-pattern)
- [Components](#components)
  - [Root Agent (Coordinator)](#root-agent-coordinator)
  - [Planning Agent](#planning-agent)
  - [Booking Agent](#booking-agent)
  - [Itinerary Agent](#itinerary-agent)
  - [MCP Payment Server](#mcp-payment-server)
- [Data Flow](#data-flow)
- [Setup & Installation](#setup--installation)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Implementation Status](#implementation-status)
- [Future Enhancements](#future-enhancements)

---

## Overview

The Travel Planner Agent is an intelligent travel concierge system that uses a **hierarchical multi-agent architecture** to decompose complex travel planning into specialized tasks:

1. **Discovery & Planning**: Search for flights and hotels
2. **User Confirmation**: Present options and await user approval
3. **Booking Simulation**: Simulate payment processing with database persistence
4. **Itinerary Generation**: Format confirmed bookings into shareable trip summaries

### Key Features

✅ **Multi-Agent Coordination**: Root coordinator delegates to specialist agents  
✅ **Human-in-the-Loop**: User confirmation required before booking execution  
✅ **Payment Simulation**: PostgreSQL-backed MCP server for realistic payment flow  
✅ **Search Integration**: SerpAPI for real-time flight and hotel data  
✅ **Confirmation Tracking**: PNR codes and booking references stored in database  
✅ **Cancellation Support**: Cancel bookings by confirmation code

---

## Architecture

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                      ROOT AGENT                             │
│              (Coordinator/Dispatcher)                       │
│   • Routes requests to specialist agents                    │
│   • Maintains session state and trip context                │
│   • Never performs substantive work directly                │
│   • Has access to payment tracking tools                    │
└────────────┬────────────────┬────────────────┬──────────────┘
             │                │                │
    ┌────────▼────────┐ ┌────▼─────────┐ ┌────▼──────────┐
    │ PLANNING AGENT  │ │BOOKING AGENT │ │ITINERARY AGENT│
    │                 │ │              │ │               │
    │ • Search flights│ │• Extract     │ │• Format day-  │
    │ • Search hotels │ │  pricing     │ │  by-day plans │
    │ • Compare       │ │• Simulate    │ │• Display      │
    │   options       │ │  payments    │ │  confirmations│
    │ • Auto-select   │ │• Track       │ │• Show payment │
    │   or present    │ │  codes       │ │  summary      │
    │ • ASK USER      │ │• Validate    │ │• Cancellation │
    │   CONFIRMATION  │ │  selections  │ │  policies     │
    └─────────────────┘ └──────────────┘ └───────────────┘
             │                │
             │                │
             ▼                ▼
    ┌─────────────────────────────────────┐
    │   MCP PAYMENT SERVER (PostgreSQL)   │
    │                                     │
    │  Tools:                             │
    │  • simulate_flight_payment          │
    │  • simulate_hotel_payment           │
    │  • cancel_payment                   │
    │  • list_payment_activity            │
    │  • ping_database                    │
    │                                     │
    │  Tables:                            │
    │  • payment_requests                 │
    │  • payment_transactions             │
    └─────────────────────────────────────┘
```

### Workflow Phases

The system operates in three sequential phases with explicit user confirmation:

#### **Phase 1: Discovery (Planning Agent)**

```
User Request
    ↓
Root → Planning Agent
    ↓
Search Tools (SerpAPI)
    ↓
Present Top Options
    ↓
⏸️  PAUSE: "Shall I proceed with booking these options?"
```

**Planning Agent Responsibilities**:

- Execute `search_flight(departure_id, arrival_id, outbound_date, return_date)`
- Execute `search_hotel(location, check_in_date, check_out_date)`
- Present top N results (default 5)
- Auto-select if user requests (e.g., "book the cheapest")
- **Ask user confirmation** before handing off to booking

**User Confirmation Triggers**:

- Explicit: "Book these options"
- Implicit: "Yes, proceed" / "Looks good"
- Autonomous: "Book the best option automatically" (skips confirmation)

#### **Phase 2: Booking (Booking Agent)**

```
User Confirmation ✓
    ↓
Root → Booking Agent
    ↓
Extract Pricing & Metadata
    ↓
Simulate Payments (MCP Tools)
    ↓
Store Confirmation Codes
```

**Booking Agent Responsibilities**:

- Receive structured selections from planning agent
- Extract pricing: `price * 100 = amount_cents`
- Call `simulate_flight_payment(airline, amount_cents, departure_airport, ...)`
- Call `simulate_hotel_payment(hotel_name, amount_cents, check_in_date, ...)`
- Capture confirmation codes (e.g., `FLT-A3F2B1`, `HTL-D4E5F6A7`)
- Store PNR (Passenger Name Record) for flights
- Hand off confirmations to itinerary agent

#### **Phase 3: Itinerary Generation (Itinerary Agent)**

```
Booking Confirmations
    ↓
Root → Itinerary Agent
    ↓
Format Day-by-Day Plan
    ↓
Display Confirmations & Payment Summary
    ↓
Deliver to User
```

**Itinerary Agent Responsibilities**:

- Assemble chronological trip timeline
- Display flight/hotel details with confirmation codes
- Show payment summary (amounts, currency, method)
- Include cancellation policies
- Provide shareable format

---

### User Confirmation Pattern

**The confirmation pattern is implemented entirely through prompts** (no custom functions needed). The key mechanism is:

1. **Planning Agent Prompt Update**:

   ```xml
   <CONFIRMATION_FLOW>
   After presenting search results:
   1. Summarize selected options (flight + hotel + total cost)
   2. Ask explicitly: "Shall I proceed with booking these options?"
   3. Wait for user response
   4. Only hand off to booking_agent if user confirms:
      - Positive signals: "yes", "book it", "proceed", "confirm", "looks good"
      - Negative signals: "no", "wait", "let me think", "show other options"
   5. If user says "book automatically" or "book the best", skip future confirmations
   </CONFIRMATION_FLOW>
   ```

2. **Root Agent Awareness**:

   ```xml
   <CONFIRMATION_TRACKING>
   Monitor conversation state:
   - If planning_agent is waiting for user confirmation, DO NOT route to booking_agent
   - Only invoke booking_agent after explicit user approval
   - If user asks to see other options, return to planning_agent
   </CONFIRMATION_TRACKING>
   ```

3. **Model's Natural Language Understanding**:
   - Gemini 2.0 Flash inherently understands confirmation semantics
   - No hardcoded state machine needed
   - The agent pauses and waits for the next user message
   - User's response determines the next action

**Example Conversation Flow**:

```
User: "Find me flights and hotels to Tokyo for Dec 1-5"

Planning Agent:
  🔍 Searching flights from SFO to NRT...
  🔍 Searching hotels in Tokyo...

  Found:
  ✈️  United UA837 | SFO → NRT | Dec 1, 11:00 AM | $850
  🏨  Hotel Gracery Shinjuku | 4 nights | $600 ($150/night)

  Total estimated cost: $1,450

  ❓ Shall I proceed with booking these options?

User: "Yes, book it"

Booking Agent:
  💳 Processing flight payment...
  ✅ Flight confirmed | Code: FLT-A3F2B1 | PNR: XYZ123

  💳 Processing hotel payment...
  ✅ Hotel confirmed | Code: HTL-D4E5F6A7

  Total charged: $1,450 USD

  Generating your itinerary...

Itinerary Agent:
  📋 TOKYO TRIP | Dec 1-5, 2025
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  DAY 1 - Monday, Dec 1
  ✈️ Outbound Flight
     United UA837 | SFO → NRT
     Departs: 11:00 AM | Arrives: 3:30 PM (+1 day)
     ✓ Confirmed | Code: FLT-A3F2B1 | PNR: XYZ123
     Price: $850

  🏨 Check-in
     Hotel Gracery Shinjuku
     4 nights | Dec 1-5
     ✓ Confirmed | Code: HTL-D4E5F6A7
     Price: $600

  [... remaining days ...]

  💳 PAYMENT SUMMARY
  Flight: $850
  Hotel: $600
  Total Paid: $1,450 USD
  Payment Method: Simulated Credit Card
```

**Alternative: User Declines**:

```
Planning Agent: "Shall I proceed with booking these options?"

User: "No, show me cheaper hotels"

Planning Agent:
  🔍 Searching for more budget-friendly options...

  Found:
  🏨 APA Hotel Shinjuku | 4 nights | $400 ($100/night)
  🏨 Toyoko Inn Tokyo | 4 nights | $350 ($87.50/night)

  Would you like to book one of these instead?
```

---

## Components

### Root Agent (Coordinator)

**File**: `travel_planner_agent/agent.py`

**Responsibilities**:

- Route user requests to appropriate specialist agents
- Maintain session state (trip context, selections, confirmations)
- Track conversation phase (pre-trip, in-trip, post-trip)
- **Never perform substantive planning or booking directly**
- Coordinate handoffs between agents
- Monitor payment activity via `list_payment_activity`

**Tools Available**:

- All MCP payment tools (for tracking and monitoring)
- Sub-agent invocation

**Model**: `gemini-2.0-flash`

**Key Prompt Sections**:

```xml
<HANDOFF_RULES>
- Route planning questions → planning_agent
- Route payment readiness → booking_agent (ONLY after user confirmation)
- Route summary requests → itinerary_agent
- Close out current task before next handoff
</HANDOFF_RULES>
```

---

### Planning Agent

**File**: `travel_planner_agent/sub_agents/planning_agent/agent.py`

**Responsibilities**:

- Discover destinations and compare options
- Search flights via `search_flight(departure_id, arrival_id, outbound_date, return_date)`
- Search hotels via `search_hotel(location, check_in_date, check_out_date)`
- Present top results (default 5)
- Auto-select if requested by user
- **ASK USER CONFIRMATION before booking**
- Capture the traveler's preferred currency and keep all quotes consistent
- Structure selections for booking agent

**Tools Available**:

- `search_flight` (SerpAPI Google Flights)
- `search_hotel` (SerpAPI Google Hotels)
- `web_search` (DuckDuckGo)

Both search tools now accept an optional `currency` parameter and honor
`SERP_API_DEFAULT_CURRENCY` / `TRAVEL_DEFAULT_CURRENCY` env vars. SerpAPI calls are
limited to `SERP_API_MAX_ATTEMPTS` (defaults to 1) to stay within the 100 requests / month quota.
Round-trip flight lookups automatically follow the `departure_token` to fetch the
return leg for up to `SERP_API_MAX_RETURN_QUERIES` outbound options (defaults to 3).

**Model**: `gemini-2.0-flash`

**Handoff Format** (to Booking Agent):

```json
{
  "selected_outbound_flight": {
    "airline": "United Airlines",
    "flight_number": "UA837",
    "departure_airport": "SFO",
    "arrival_airport": "NRT",
    "departure_time": "11:00",
    "arrival_time": "15:30+1",
    "price": 850,
    "duration": "11h 30m"
  },
  "selected_return_flight": { ... },
  "selected_hotel": {
    "name": "Hotel Gracery Shinjuku",
    "address": "1-2-3 Kabukicho, Shinjuku",
    "check_in_date": "2025-12-01",
    "check_out_date": "2025-12-05",
    "price_per_night": 150,
    "total_price": 600,
    "rating": 4.5
  },
  "total_estimated_cost": 1450,
   "currency_code": "USD",
  "user_confirmed": true
}
```

**Enhanced Prompt Sections** (TODO):

```xml
<CONFIRMATION_FLOW>
After presenting search results:
1. Summarize selected options clearly
2. Ask: "Shall I proceed with booking these options?"
3. Wait for user response
4. Only hand off to booking_agent if confirmed
5. Autonomous mode: user says "book automatically" → skip confirmations
</CONFIRMATION_FLOW>

<HANDOFF_TO_BOOKING>
Before escalating, populate:
- selected_outbound_flight
- selected_return_flight (if round trip)
- selected_hotel
- total_estimated_cost
- user_confirmed: true

Pass summary to booking_agent:
"Planning complete. Selected [details]. User confirmed. Ready for booking."
</HANDOFF_TO_BOOKING>
```

---

### Booking Agent

**File**: `travel_planner_agent/sub_agents/booking_agent/agent.py`

**Responsibilities**:

- Receive confirmed selections from planning agent
- Extract pricing and convert to cents (`price * 100`)
- Extract booking metadata (names, dates, airports)
- Call `simulate_flight_payment(...)` with extracted data
- Call `simulate_hotel_payment(...)` with extracted data
- Capture and store confirmation codes
- Track PNR for flights
- Validate payment success
- Hand off confirmations to itinerary agent
- Ensure every payment simulation uses the traveler-selected ISO 4217 currency code

**Tools Available** (TODO: Add):

- `simulate_flight_payment`
- `simulate_hotel_payment`
- `cancel_payment`
- `list_payment_activity`

**Model**: `gemini-2.0-flash`

**Payment Extraction Logic** (TODO: Add to Prompt):

```xml
<PAYMENT_WORKFLOW>
1. Extract pricing from planning_agent's selections:
   - Flight: selection.price * 100 = amount_cents
   - Hotel: selection.total_price * 100 = amount_cents

2. Extract metadata:
   - Flight: airline, flight_number, departure_airport, arrival_airport, departure_date, passenger_name
   - Hotel: hotel_name, address, check_in_date, check_out_date, guest_name

3. Call payment simulation:
   simulate_flight_payment(
     airline=selection.airline,
     amount_cents=int(selection.price * 100),
     currency="USD",
     departure_airport=selection.departure_airport,
     arrival_airport=selection.arrival_airport,
     departure_date=selection.departure_date,
     passenger_name=user_profile.name or "Guest",
     session_id=session.id
   )

4. Store confirmation:
   - flight_confirmation_code = response.payment_transaction.confirmation_code
   - flight_pnr = response.payment_transaction.vendor_reference

5. Repeat for hotel booking

6. Verify both confirmations received

7. Prepare handoff to itinerary_agent with full confirmation package
</PAYMENT_WORKFLOW>
```

---

### Itinerary Agent

**File**: `travel_planner_agent/sub_agents/itinerary_agent/agent.py`

**Responsibilities**:

- Receive booking confirmations from booking agent
- Assemble chronological day-by-day itinerary
- Display flight/hotel details with confirmation codes
- Format payment summary
- Include cancellation policies
- Provide professional, emoji-free output that can be exported to files

**Tools Available**:

- `save_itinerary_file` (Markdown/plain text export)
- `save_itinerary_calendar` (.ics calendar export)

**Model**: `gemini-2.0-flash`

**Input Expected** (from Booking Agent):

```json
{
  "flight_confirmation_code": "FLT-A3F2B1",
  "flight_pnr": "XYZ123",
  "hotel_confirmation_code": "HTL-D4E5F6A7",
  "flight_total_paid": 850,
  "hotel_total_paid": 600,
  "payment_currency": "USD",
  "outbound_flight_selection": { ... },
  "hotel_selection": { ... }
}
```

**Enhanced Prompt Sections** (TODO):

```xml
<CONFIRMATION_DISPLAY>
Use clear section headings instead of emojis:
- Flight: "Status: Confirmed | Code: [code] | PNR: [pnr] | Paid: [amount currency]"
- Hotel: "Status: Confirmed | Code: [code] | Paid: [amount currency]"
- Total paid: "[currency] [total]"
- Payment method: "Simulated Credit Card"
</CONFIRMATION_DISPLAY>

<CANCELLATION_NOTES>
Remind user:
"To cancel, provide the confirmation code to the booking agent."
Display cancellation windows and policies if available.
</CANCELLATION_NOTES>
```

---

### MCP Payment Server

**File**: `travel_planner_agent/mcp_servers/postgres_payments/server.py`

A Model Context Protocol server that exposes payment simulation tools backed by PostgreSQL.

**Database Schema**:

```sql
-- Payment requests (one per booking)
CREATE TABLE payment_requests (
    id BIGSERIAL PRIMARY KEY,
    vendor TEXT NOT NULL,              -- Airline or hotel name
    amount_cents INTEGER NOT NULL,     -- Price in cents
    currency TEXT NOT NULL,            -- e.g., "USD"
    session_id TEXT,                   -- ADK session ID
    user_id TEXT,                      -- User identifier
    metadata JSONB DEFAULT '{}'::jsonb, -- Booking details
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Payment transactions (one per payment_request)
CREATE TABLE payment_transactions (
    id BIGSERIAL PRIMARY KEY,
    request_id BIGINT NOT NULL REFERENCES payment_requests(id) ON DELETE CASCADE,
    status TEXT NOT NULL,              -- "confirmed", "cancelled"
    confirmation_code TEXT NOT NULL,   -- e.g., "FLT-A3F2B1"
    vendor_reference TEXT,             -- PNR or hotel booking ID
    session_id TEXT,
    user_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb, -- Payment method, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**MCP Tools Exposed**:

1. **`ping_database()`**

   - Lightweight connectivity check
   - Returns pool status and timestamp

2. **`list_payment_activity(limit=20)`**

   - Query recent payment requests and transactions
   - Join data from both tables
   - Filter by session_id if needed

3. **`simulate_flight_payment(...)`**

   - Creates payment_request for flight
   - Generates confirmation code (e.g., `FLT-A3F2B1`)
   - Generates PNR (e.g., `XYZ123`)
   - Creates payment_transaction with status "confirmed"
   - Returns full transaction details

4. **`simulate_hotel_payment(...)`**

   - Creates payment_request for hotel
   - Generates confirmation code (e.g., `HTL-D4E5F6A7`)
   - Creates payment_transaction with status "confirmed"
   - Returns full transaction details

5. **`cancel_payment(confirmation_code, reason=None)`**
   - Looks up transaction by confirmation code
   - Updates status to "cancelled"
   - Stores cancellation reason and timestamp in metadata
   - Returns updated transaction

**Connection**:

- Uses `psycopg_pool.AsyncConnectionPool`
- Configured via `PAYMENTS_DB_URL` environment variable
- Global state pattern (no request context dependency)

**Registration**:

```python
# In travel_planner_agent/tools/mcp.py
if os.getenv("PAYMENTS_DB_URL"):
    AVAILABLE_MCP_TOOLSETS = [
        MCPToolset(
            server_params=StdioServerParameters(
                command="python",
                args=["-m", "travel_planner_agent.mcp_servers.postgres_payments.server"],
            )
        )
    ]
```

---

### Itinerary Export MCP Server

**File**: `travel_planner_agent/mcp_servers/itinerary_export/server.py`

Provides lightweight tools so agents can persist itineraries for users who want to
download the plan to their phone or laptop.

**Tools Exposed**:

1. **`save_itinerary_file(filename, content, format="md", subdirectory=None)`**

   - Writes Markdown or plain-text content to the exports directory
   - Returns the saved path and byte count

2. **`save_itinerary_calendar(filename, events, subdirectory=None)`**
   - Accepts a list of `{summary, start, end, description, location}` events
   - Emits a standards-compliant `.ics` file that travelers can import into Calendar apps

**Configuration**:

- `ITINERARY_EXPORT_DIR` or `TRAVEL_EXPORT_DIR` (optional): override the default
  exports directory (defaults to `<repo>/exports`).
- Files are written with sanitized names to prevent path traversal.

The same MCP toolset is shared with the root, booking, and itinerary agents so any
of them can fulfill “save/share my itinerary” requests.

---

## Data Flow

### Full Booking Flow

```
┌─────────────┐
│    USER     │
│"Book Tokyo" │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    ROOT AGENT                               │
│  Analyzes intent → Routes to planning_agent                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                 PLANNING AGENT                              │
│  1. search_flight("SFO", "NRT", "2025-12-01", "2025-12-05") │
│     → Returns: [{airline: "United", price: 850, ...}, ...]  │
│  2. search_hotel("Tokyo", "2025-12-01", "2025-12-05")       │
│     → Returns: [{name: "Hotel Gracery", price: 600, ...}]   │
│  3. Auto-select or present top options                      │
│  4. ⏸️  ASK USER: "Shall I proceed with booking?"           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                     ┌──────▼──────┐
                     │USER: "Yes"  │
                     └──────┬──────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     ROOT AGENT                              │
│  User confirmed → Routes to booking_agent                   │
│  Passes: {selected_flight, selected_hotel, user_confirmed}  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   BOOKING AGENT                             │
│  1. Extract: flight_price = 850 * 100 = 85000 cents        │
│  2. Extract: hotel_price = 600 * 100 = 60000 cents         │
│  3. Call: simulate_flight_payment(                          │
│       airline="United",                                     │
│       amount_cents=85000,                                   │
│       departure_airport="SFO",                              │
│       arrival_airport="NRT",                                │
│       departure_date="2025-12-01",                          │
│       session_id=session.id                                 │
│     )                                                       │
│     → MCP Server inserts to DB                              │
│     → Returns: {confirmation_code: "FLT-A3F2B1",            │
│                 vendor_reference: "XYZ123"}                 │
│  4. Store: flight_confirmation = "FLT-A3F2B1"               │
│  5. Store: flight_pnr = "XYZ123"                            │
│  6. Call: simulate_hotel_payment(...)                       │
│     → Returns: {confirmation_code: "HTL-D4E5F6A7"}          │
│  7. Store: hotel_confirmation = "HTL-D4E5F6A7"              │
│  8. Prepare handoff package with all confirmations          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     ROOT AGENT                              │
│  Bookings complete → Routes to itinerary_agent              │
│  Passes: {flight_conf, hotel_conf, payment_totals, ...}     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ITINERARY AGENT                            │
│  1. Assemble day-by-day timeline                            │
│  2. Format flight with: "✓ FLT-A3F2B1 | PNR: XYZ123"        │
│  3. Format hotel with: "✓ HTL-D4E5F6A7"                     │
│  4. Display payment summary: "Total: $1,450 USD"            │
│  5. Output shareable itinerary                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
                      ┌──────────┐
                      │   USER   │
                      │ Receives │
                      │ Itinerary│
                      └──────────┘
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Google Cloud Project (for Vertex AI / Gemini API)
- SerpAPI Key (for flight/hotel search)

### Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/hanjihun2000/travel-planner-agent.git
   cd travel-planner-agent
   ```

2. **Create virtual environment**:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # .venv\Scripts\activate    # On Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL**:

   ```bash
   # Create database
   createdb travel_payments

   # Schema will be auto-created on first run
   ```

5. **Configure environment variables**:

   ```bash
   # Create .env file
   cat > .env << EOF
   # PostgreSQL
   PAYMENTS_DB_URL=postgresql://user:password@localhost:5432/travel_payments

   # SerpAPI
   SERP_API_KEY=your_serpapi_key_here
   SERP_API_DEFAULT_CURRENCY=USD
   TRAVEL_DEFAULT_CURRENCY=USD
   SERP_API_MAX_ATTEMPTS=1
   SERP_API_MAX_RETURN_QUERIES=3

   # Google Cloud (for Vertex AI)
   GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   GOOGLE_CLOUD_PROJECT=your-project-id

   # Optional: MCP Server Logging
   PAYMENTS_MCP_LOG_LEVEL=INFO
   ITINERARY_EXPORT_DIR=./exports
   ITINERARY_EXPORT_LOG_LEVEL=INFO
   EOF
   ```

6. **Run the ADK web server**:

   ```bash
   adk web
   ```

7. **Access the UI**:
   - Navigate to `http://127.0.0.1:8000`
   - Start a new session
   - Begin chatting with the travel planner

---

## Usage Examples

### Example 1: Simple Flight + Hotel Search with Confirmation

```
User: "Find me a trip to Tokyo for December 1-5"

Planning Agent:
  🔍 Searching flights from SFO to NRT (Dec 1-5)...
  🔍 Searching hotels in Tokyo...

  Top Options:

  ✈️  Flight
      United UA837 | SFO → NRT
      Departs: Dec 1, 11:00 AM | Arrives: Dec 2, 3:30 PM
      Price: $850

  🏨  Hotel
      Hotel Gracery Shinjuku
      4 nights | Dec 1-5
      Rating: 4.5/5 | Price: $600 ($150/night)

  💰 Total Estimated Cost: $1,450

  ❓ Shall I proceed with booking these options?

User: "Yes, book it"

Booking Agent:
  💳 Processing flight payment for United UA837...
  ✅ Flight confirmed!
     Confirmation Code: FLT-3A7B2C
     PNR: KLM9X4
     Amount Charged: $850 USD

  💳 Processing hotel payment for Hotel Gracery Shinjuku...
  ✅ Hotel confirmed!
     Confirmation Code: HTL-9D2E5F1A
     Amount Charged: $600 USD

  📋 Total charged: $1,450 USD

  Generating your itinerary...

Itinerary Agent:
  📋 TOKYO ADVENTURE | December 1-5, 2025
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  DAY 1 - Monday, December 1
  ✈️ Outbound Flight
     United Airlines UA837
     SFO (San Francisco) → NRT (Tokyo Narita)
     Departs: 11:00 AM | Arrives: 3:30 PM (+1 day)
     Duration: 11h 30m
     ✓ Confirmed | Code: FLT-3A7B2C | PNR: KLM9X4
     Price: $850

  DAY 2 - Tuesday, December 2
  🏨 Check-in
     Hotel Gracery Shinjuku
     1-2-3 Kabukicho, Shinjuku-ku, Tokyo
     Check-in: 3:00 PM
     ✓ Confirmed | Code: HTL-9D2E5F1A
     4 nights | $600 total ($150/night)

  [... Days 3-4 with suggested activities ...]

  DAY 5 - Friday, December 5
  🏨 Check-out
     Hotel Gracery Shinjuku
     Check-out: 11:00 AM

  ✈️ Return Flight
     [Awaiting selection]

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💳 PAYMENT SUMMARY
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Flight (Outbound):     $850
  Hotel (4 nights):      $600
  ───────────────────────────
  Total Paid:            $1,450 USD
  Payment Method:        Simulated Credit Card

  📝 IMPORTANT NOTES
  • Free cancellation until Nov 24, 2025
  • Hotel check-in requires valid ID
  • To cancel, provide confirmation codes to booking agent

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Example 2: User Declines Initial Options

```
Planning Agent:
  ❓ Shall I proceed with booking these options?
  Total: $1,450

User: "That's too expensive. Show me cheaper hotels."

Planning Agent:
  🔍 Searching for more budget-friendly hotels...

  Found:
  🏨  APA Hotel Shinjuku
      4 nights | $400 ($100/night)
      Rating: 4.2/5

  🏨  Toyoko Inn Tokyo Ikebukuro
      4 nights | $350 ($87.50/night)
      Rating: 4.0/5

  Updated total with APA Hotel: $1,250

  Would you like to book the United flight + APA Hotel?

User: "Yes, that works"

[... proceeds to booking ...]
```

### Example 3: Cancellation

```
User: "Cancel my hotel booking HTL-9D2E5F1A"

Root Agent → Booking Agent

Booking Agent:
  🔍 Looking up booking HTL-9D2E5F1A...

  Found:
  Hotel Gracery Shinjuku
  4 nights | Dec 1-5
  Amount: $600
  Status: confirmed

  Cancelling booking...

  ✅ Booking cancelled successfully
     Confirmation: HTL-9D2E5F1A
     Status: cancelled
     Refund: $600 will be processed within 5-7 business days
```

### Example 4: View Booking History

```
User: "Show me all my bookings"

Root Agent:
  📋 Retrieving your booking history...

  Recent Bookings:

  1. Flight - United UA837
     Date: Dec 1, 2025
     Code: FLT-3A7B2C | PNR: KLM9X4
     Amount: $850 | Status: ✅ Confirmed

  2. Hotel - Hotel Gracery Shinjuku
     Dates: Dec 1-5, 2025
     Code: HTL-9D2E5F1A
     Amount: $600 | Status: ❌ Cancelled

  Total Paid: $850 (after cancellation)
```

---

## Testing

### Manual Testing Checklist

#### Scenario 1: Full Autonomous Booking

- [ ] User: "Book the cheapest flight and hotel to Tokyo for Dec 1-5"
- [ ] Planning agent searches and auto-selects
- [ ] Booking agent processes payments
- [ ] Itinerary shows confirmations
- [ ] Database has 2 requests + 2 transactions

#### Scenario 2: User Confirmation Flow

- [ ] User: "Find flights to Tokyo"
- [ ] Planning shows options
- [ ] Planning asks: "Shall I proceed?"
- [ ] User: "Yes"
- [ ] Booking executes
- [ ] Confirmations displayed

#### Scenario 3: User Declines and Requests Alternatives

- [ ] Planning presents options
- [ ] User: "No, show cheaper hotels"
- [ ] Planning searches again
- [ ] User confirms new options
- [ ] Booking proceeds

#### Scenario 4: Cancellation

- [ ] User: "Cancel HTL-9D2E5F1A"
- [ ] Booking agent calls `cancel_payment`
- [ ] Database status → "cancelled"
- [ ] User receives confirmation

#### Scenario 5: Payment History

- [ ] User: "Show my bookings"
- [ ] Root calls `list_payment_activity`
- [ ] Displays all transactions

#### Scenario 6: Database Connectivity

- [ ] Start server
- [ ] Call `ping_database`
- [ ] Returns pool status
- [ ] No errors

### Automated Testing (Future)

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Test MCP server standalone
python -m travel_planner_agent.mcp_servers.postgres_payments.server
```

---

## Implementation Status

### ✅ Completed

- [x] Root agent with coordinator pattern
- [x] Planning agent with search tools
- [x] Booking agent structure
- [x] Itinerary agent structure
- [x] MCP payment server with PostgreSQL
- [x] `simulate_flight_payment` tool
- [x] `simulate_hotel_payment` tool
- [x] `cancel_payment` tool
- [x] `list_payment_activity` tool
- [x] `ping_database` tool
- [x] Database schema with session/user tracking
- [x] Global state pattern (no context dependency)
- [x] MCP toolset registration

### 🚧 In Progress

- [ ] Add MCP tools to booking_agent (`tools=AVAILABLE_MCP_TOOLSETS`)
- [ ] Update planning_agent prompt with confirmation flow
- [ ] Update booking_agent prompt with payment workflow
- [ ] Update itinerary_agent prompt with confirmation display
- [ ] Test end-to-end user confirmation pattern
- [ ] Validate payment extraction from search results

### 📋 Planned

- [ ] Add search tools to planning_agent (SerpAPI integration)
- [ ] Session memory helpers for tracking selections
- [ ] Price extraction utilities
- [ ] Confirmation code validation
- [ ] Multi-leg flight support
- [ ] Multi-traveler bookings
- [ ] Real-time price monitoring
- [ ] Loyalty program integration
- [ ] Email confirmation sending
- [ ] Calendar integration

---

## Future Enhancements

### Short Term

- **Error Recovery**: Retry logic for payment failures
- **Price Validation**: Check if prices changed between search and booking
- **Seat Selection**: Add seat preference collection
- **Room Types**: Support room category selection (standard, deluxe, suite)

### Medium Term

- **Multi-City Trips**: Support complex itineraries (NYC → Tokyo → Paris)
- **Ground Transportation**: Add car rentals and train bookings
- **Activities**: Integrate tour and activity bookings
- **Travel Insurance**: Offer insurance options

### Long Term

- **Real Payment Integration**: Connect to Stripe/PayPal
- **Airline GDS Integration**: Real-time inventory checks
- **Hotel Direct Booking**: API connections to hotel chains
- **Loyalty Programs**: Track and redeem points
- **Mobile App**: Native iOS/Android companion
- **Voice Interface**: Integrate with voice assistants

---

## Architecture Principles

### 1. Hierarchical Task Decomposition

Complex travel planning is broken into specialist roles, each with clear boundaries.

### 2. Human-in-the-Loop

User confirmation required before financial transactions, maintaining trust and control.

### 3. Separation of Concerns

- Root: Routes and coordinates
- Planning: Discovers and presents
- Booking: Executes and confirms
- Itinerary: Formats and delivers

### 4. Stateful Conversations

ADK session management tracks context across agent handoffs.

### 5. Extensibility

MCP protocol allows adding payment providers, booking engines, or analytics without core changes.

### 6. Realistic Simulation

PostgreSQL-backed payments mirror production workflows for testing and demos.

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

[MIT License](LICENSE)

---

## Acknowledgments

- **Google ADK Team**: Agent framework and orchestration
- **Model Context Protocol**: Tool integration standard
- **SerpAPI**: Flight and hotel search data
- **PostgreSQL**: Reliable payment simulation backend

---

## Support

For questions or issues:

- Open a GitHub issue
- Check ADK documentation: https://github.com/google/adk-python

---

**Built with ❤️ using Google ADK and Gemini 2.0**
