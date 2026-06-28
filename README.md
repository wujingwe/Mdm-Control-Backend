# MdM Control Backend

Backend service for MDM (Mobile Device Management) control plane. Built with FastAPI, async SQLAlchemy, MariaDB, and optional Kafka.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Next.js FE │────▶│  FastAPI API │────▶│  SSE Server    │
│  (webhook)  │◀────│  (this app)  │     │  (external)    │
└─────────────┘     └──────┬───────┘     └────────────────┘
                           │
                           ▼
                     ┌──────────┐     ┌──────────────┐
                     │  MariaDB │────▶│  Kafka (opt) │
                     └──────────┘     └──────────────┘
```

- **API** — FastAPI async endpoints at `/api/v1/*` (see [API.md](API.md))
- **Database** — MariaDB via `aiomysql` + SQLAlchemy 2.0 async ORM
- **Messaging** — Kafka (`aiokafka`) optional, for async policy push to devices
- **SSE Notification** — API calls an external SSE server directly when policies are assigned to groups
- **Webhook** — Mutations notify Next.js for ISR cache revalidation

## Prerequisites

- Python 3.12+
- MariaDB running on `localhost:3306` with database `mdm_control`
- Kafka broker on `localhost:9092` (optional — the app runs without it)

## Setup

```sh
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env` (defaults are pre-configured) and adjust as needed.

## Configuration

All settings via `.env` file or environment variables:

| Variable | Default | Description |
|---|---|---|
| `DB_URL` | `mysql+aiomysql://jing-weiwu:mdm@localhost:3306/mdm_control` | Database connection string |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `KAFKA_TOPIC` | `policy-assignments` | Kafka topic for policy events |
| `KAFKA_GROUP_ID` | `mdm-control-group` | Consumer group ID |
| `WEBHOOK_URL` | `http://localhost:3000/api/v1/revalidate` | Next.js revalidation endpoint |
| `SSE_SERVER_URL` | `http://0.0.0.0:8080/notify` | External SSE server endpoint |
| `SSO_ENABLED` | `False` | Enable SSO authentication |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Run

```sh
uvicorn app.main:app --reload
```

OpenAPI docs at `http://localhost:8000/docs`.

## Database Migrations

This project uses **Alembic** for schema migrations.

```sh
# Apply any pending migrations (run first when setting up)
alembic upgrade head

# Generate a new migration after editing models
alembic revision --autogenerate -m "description of change"

# Rollback one step
alembic downgrade -1
```

The migration script reads `DB_URL` from `.env` automatically.

## Seed Data

```sh
venv/bin/python seed.py
```

Populates the database with sample roles, users, devices, groups, policies, and assignments.

## Type Checking

```sh
mypy app/
```

## Tests

```sh
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database with `aiosqlite`. Kafka is not required to run tests.

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI app, lifespan, middleware, health check
│   ├── config.py               # Pydantic settings from .env
│   ├── database.py             # Async engine & session factory
│   ├── webhook_client.py       # Next.js ISR revalidation helper
│   ├── core/
│   │   ├── exceptions.py       # Custom exception classes
│   │   └── security.py         # Auth / JWT utilities
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── base.py             # Declarative base & utcnow helper
│   │   ├── device.py           # Device model
│   │   ├── device_policy.py    # Device <-> Policy association
│   │   ├── group.py            # Group model (smart/static)
│   │   ├── group_policy.py     # Group <-> Policy association
│   │   ├── policy.py           # Policy model with JSON settings
│   │   ├── role.py             # Role model
│   │   ├── user.py             # User model
│   │   └── types.py            # Custom SQLAlchemy type decorators
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── common.py           # PaginatedResponse, Message
│   │   ├── device.py           # Device schemas
│   │   ├── group.py            # Group schemas
│   │   ├── policy.py           # Policy schemas
│   │   ├── role.py             # Role schemas
│   │   └── user.py             # User schemas
│   ├── repositories/           # Data access layer
│   │   ├── base.py             # Generic CRUD base repository
│   │   ├── device.py
│   │   ├── group.py
│   │   ├── policy.py
│   │   ├── role.py
│   │   └── user.py
│   ├── services/               # Business logic layer
│   │   ├── device.py           # Device service (search, assign policy)
│   │   ├── group.py            # Group service (CRUD, assign policy)
│   │   ├── policy.py           # Policy service (CRUD)
│   │   ├── role.py             # Role service
│   │   ├── user.py             # User service
│   │   ├── kafka_producer.py   # Producer singleton (optional)
│   │   ├── kafka_consumer.py   # Background consumer task (optional)
│   │   ├── sse_notify.py       # SSE server notification helpers
│   │   ├── webhook.py          # Webhook dispatch logic
│   └── api/v1/                 # Route handlers
│       ├── router.py           # Router aggregation
│       ├── devices.py          # Device endpoints
│       ├── groups.py           # Group endpoints
│       ├── policies.py         # Policy endpoints
│       ├── roles.py            # Role endpoints
│       ├── users.py            # User endpoints
│       └── metrics.py          # Fleet metrics endpoint
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
├── tests/                      # Async test suite (SQLite in-memory)
├── seed.py                     # Database seeder
├── API.md                      # Public endpoint reference
├── requirements.txt
└── pyproject.toml              # Pytest & mypy config
```

## API Endpoints

Full reference at [API.md](API.md).

### Groups

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/groups` | List all groups |
| `GET` | `/groups/{id}` | Get group by ID |
| `POST` | `/groups` | Create a group |
| `PUT` | `/groups/{id}` | Update a group |
| `DELETE` | `/groups/{id}` | Delete a group |
| `POST` | `/groups/{id}/policies` | Assign a policy to a group |

### Policies

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/policies` | List all policies |
| `GET` | `/policies/{id}` | Get policy by ID |
| `POST` | `/policies` | Create a policy |
| `PUT` | `/policies/{id}` | Update a policy |
| `POST` | `/policies/{id}/push` | Push policy via Kafka |

### Devices

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/devices` | List all devices |
| `GET` | `/devices/{id}` | Get device by ID |
| `POST` | `/devices/search` | Search devices by criteria |
| `POST` | `/devices/{id}/policy` | Assign policy to device |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users` | List all users |
| `GET` | `/roles` | List all roles |
| `GET` | `/metrics/fleet` | Fleet overview metrics |
| `GET` | `/health` | Health check |

## Flow: Assign Policy to Group

```
Web UI ──POST──▶ FastAPI ──INSERT──▶ group_policies table
                         │
                         └──POST──▶ SSE Server (http://0.0.0.0:8080/notify)
                                      { group_id, group_name, policy: { id, name } }
```

1. User selects a policy in the group detail page and clicks **Assign**
2. `POST /api/v1/groups/{id}/policies?policy_id=X` creates the association in `group_policies`
3. Backend sends an SSE notification to the external SSE server with group + policy info
4. The SSE server can then push real-time updates to connected clients
5. If the SSE server is unreachable, the assignment still succeeds (failure is logged)

## Flow: Assign Policy to Device

```
Web UI ──POST──▶ FastAPI ──INSERT──▶ device_policies table
                         │
                         ├──KAFKA──▶ Consumer ──SSE──▶ Device
                         │
                         └──SSE────▶ SSE Server (external)
```

Kafka is optional. When unavailable, the app starts and operates without messaging.

## SSE Notification Payloads

**Group policy assignment:**
```json
{
  "group_id": 1,
  "group_name": "Engineering",
  "policy": {
    "id": 1,
    "name": "Base Security Policy"
  }
}
```

**Device policy assignment:**
```json
{
  "device_serial_number": "SN001",
  "device_name": "Device 1",
  "policy": {
    "id": 1,
    "name": "Enforce Encryption",
    "config": { "key": "value" }
  }
}
```
