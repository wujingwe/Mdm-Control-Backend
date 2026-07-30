# MDM Control Backend

Backend service for a Mobile Device Management (MDM) control plane. Manages device enrollment, configuration profiles, group scoping, and command dispatch.

Built with FastAPI, async SQLAlchemy, MariaDB, and optional RabbitMQ.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Next.js FE │────▶│  FastAPI API │────▶│  SSE Server    │
│  (webhook)  │◀────│  (this app)  │     │  (external)    │
└─────────────┘     └──────┬───────┘     └────────────────┘
                           │
                           ▼
                     ┌──────────┐     ┌──────────────┐
                     │  MariaDB │     │  RabbitMQ    │
                     └──────────┘     │  (optional)  │
                                      └──────────────┘
```

- **API** — FastAPI async endpoints at `/api/v1/*` (see [API.md](API.md))
- **Database** — MariaDB via `aiomysql` + SQLAlchemy 2.0 async ORM
- **Messaging** — RabbitMQ (`aio_pika`) optional, for async profile/command push to devices
- **SSE Notification** — API calls an external SSE server directly when profiles are assigned
- **Webhook** — Mutations notify Next.js for ISR cache revalidation

## Language

See [CONTEXT.md](CONTEXT.md) for the domain glossary. Key terms:

- **Profile** — a versioned, scoppable configuration entity. *Not* "Policy".
- **Policy** — the configuration payload *inside* a Profile.
- **SmartGroup** / **StaticGroup** — dynamic and static device groups.
- **ProfileAssignment** — versioned record linking a Profile to a Device.

## Prerequisites

- Python 3.12+
- MariaDB running on `localhost:3306` with database `mdm_control`
- RabbitMQ on `localhost:5672` (optional — the app runs without it)

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
|---|---|---|---|
| `DB_URL` | `mysql+aiomysql://jing-weiwu:mdm@localhost:3306/mdm_control` | Database connection string |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | AMQP connection URL |
| `WEBHOOK_URL` | `http://localhost:3000/api/v1/revalidate` | Next.js revalidation endpoint |
| `REVALIDATION_SECRET` | — | Shared webhook secret |
| `SSE_SERVER_URL` | `http://0.0.0.0:8080/notify` | External SSE server endpoint |
| `SSO_ENABLED` | `False` | Enable SSO authentication |
| `SSO_JWKS_URL` | — | JWKS URL for JWT verification |
| `SSO_ISSUER` | — | Expected JWT issuer |
| `SSO_AUDIENCE` | — | Expected JWT audience |
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `MOCK_DB` | `false` | Use in-memory SQLite instead of MariaDB |

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
python -m app.mock.seed
```

Populates the database with sample roles, users, devices, groups, profiles, and assignments.

## Type Checking

```sh
mypy app/
```

## Tests

```sh
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database with `aiosqlite`. RabbitMQ is not required to run tests.

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI app, lifespan, middleware, health check
│   ├── database.py             # Async SQLAlchemy engine & session factory
│   ├── dependencies.py         # FastAPI dependency injection
│   ├── lifecycle.py            # App lifecycle (start/stop RabbitMQ, etc.)
│   ├── webhook_client.py       # Next.js ISR revalidation helper
│   ├── base.py                 # SQLAlchemy declarative base & utcnow helper
│   ├── types.py                # Custom SQLAlchemy type decorators
│   ├── config/
│   │   └── settings.py         # Pydantic settings from .env
│   ├── core/
│   │   ├── exceptions.py       # Custom exception classes
│   │   └── security.py         # Auth / JWT utilities
│   ├── common/
│   │   ├── enums.py            # Shared enumerations
│   │   └── schemas.py          # PaginatedResponse, Scope, Message
│   ├── profiles/               # Configuration profiles
│   │   ├── models.py           # Profile, ProfileAssignment ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── repositories.py     # Data access layer
│   │   ├── services.py         # Business logic
│   │   └── reconciler.py       # ProfileAssignment calculation engine
│   ├── smart_groups/           # Dynamic device groups (criteria-based)
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── static_groups/          # Explicit device groups
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── devices/                # Device management
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── commands/               # Device commands (lock, wipe, restart, etc.)
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── mobile_apps/            # Mobile application distribution
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── extension_attributes/   # Custom device metadata fields
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── inventory_search/       # Saved device search queries
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── users/                  # User management
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repositories.py
│   │   └── services.py
│   ├── messaging/              # RabbitMQ producer & consumer
│   │   ├── producer.py         # Publisher (profile push/revoke, commands)
│   │   └── consumer.py         # Background consumer for device status
│   ├── notification/           # SSE server notification helpers
│   ├── criteria/               # Smart group criteria evaluation
│   │   └── schemas.py
│   ├── mock/
│   │   └── seed.py             # Database seeder
│   ├── api/v1/                 # Route handlers
│   │   ├── router.py           # Router aggregation
│   │   ├── profiles.py         # Profile endpoints
│   │   ├── smart_groups.py     # Smart group endpoints
│   │   ├── static_groups.py    # Static group endpoints
│   │   ├── devices.py          # Device + check-in + command endpoints
│   │   ├── mobile_apps.py      # Mobile app endpoints
│   │   ├── extension_attributes.py
│   │   ├── inventory_search.py # Saved search endpoints
│   │   └── users.py            # User endpoints
│   └── worker.py               # Standalone RabbitMQ consumer process
├── alembic/
│   ├── env.py
│   └── versions/
├── tests/                      # Async test suite (SQLite in-memory)
├── docs/
│   └── adr/                    # Architecture decision records
├── API.md
├── CONTEXT.md                  # Domain glossary
├── DATABASE.md
├── Models.md
├── requirements.txt
├── Makefile
├── pyproject.toml
├── mypy.ini
├── ruff.toml
└── skills-lock.json
```

## API Endpoints

Full reference at [API.md](API.md).

### Profiles

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/profiles` | List all profiles |
| `GET` | `/profiles/{id}` | Get profile by ID |
| `POST` | `/profiles` | Create a profile |
| `PUT` | `/profiles/{id}` | Update a profile |
| `DELETE` | `/profiles/{id}` | Delete a profile |
| `GET` | `/profiles/{id}/assignments` | List profile assignments |
| `PUT` | `/profiles/{id}/assignments/{device_id}/status` | Update assignment status |

### Smart Groups

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/smart-groups` | List all smart groups |
| `GET` | `/smart-groups/{id}` | Get group by ID |
| `POST` | `/smart-groups` | Create a smart group |
| `PUT` | `/smart-groups/{id}` | Update a group |
| `DELETE` | `/smart-groups/{id}` | Delete a group |

### Static Groups

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/static-groups` | List all static groups |
| `GET` | `/static-groups/{id}` | Get group by ID |
| `POST` | `/static-groups` | Create a static group |
| `PUT` | `/static-groups/{id}` | Update a group |
| `DELETE` | `/static-groups/{id}` | Delete a group |

### Devices

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/devices` | List all devices |
| `GET` | `/devices/{id}` | Get device by ID |
| `PUT` | `/devices/{id}` | Update a device |
| `POST` | `/devices/{id}/check-in` | Device check-in (recalculate + dispatch) |
| `GET` | `/devices/{id}/commands` | List device commands |
| `GET` | `/devices/{id}/commands/{command_id}` | Get command |
| `POST` | `/devices/{id}/commands` | Execute a command on a device |

### Mobile Apps

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/mobile-apps` | List all mobile apps |
| `GET` | `/mobile-apps/{id}` | Get app by ID |
| `POST` | `/mobile-apps` | Create a mobile app |
| `PUT` | `/mobile-apps/{id}` | Update a mobile app |
| `DELETE` | `/mobile-apps/{id}` | Delete a mobile app |

### Extension Attributes

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/extension-attributes` | List all extension attributes |
| `GET` | `/extension-attributes/{id}` | Get attribute by ID |
| `POST` | `/extension-attributes` | Create an extension attribute |
| `PUT` | `/extension-attributes/{id}` | Update an extension attribute |
| `DELETE` | `/extension-attributes/{id}` | Delete an extension attribute |

### Inventory Search

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/inventory-search` | List saved searches |
| `GET` | `/inventory-search/{id}` | Get search by ID |
| `POST` | `/inventory-search` | Create a saved search |
| `PUT` | `/inventory-search/{id}` | Update a saved search |
| `DELETE` | `/inventory-search/{id}` | Delete a saved search |
| `POST` | `/inventory-search/{id}/execute` | Execute a search |

### Other

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users` | List all users |
| `GET` | `/users/{id}` | Get user by ID |
| `POST` | `/users` | Create a user |
| `PUT` | `/users/{id}` | Update a user |
| `DELETE` | `/users/{id}` | Delete a user |
| `GET` | `/users/by-email/{email}` | Lookup user by email |
| `GET` | `/health` | Health check |

## Flow: Profile Assignment

Group scope changes and device updates trigger the `ProfileAssignmentReconciler`, which:

1. Recalculates desired state (PRESENT/ABSENT) for all affected (profile, device) pairs
2. Writes new assignment revision rows (append-only)
3. Publishes profile push/revoke events to RabbitMQ (`mdm.device.commands` exchange)
4. Optionally dispatches the latest revision via SSE during device check-in

### Group scope change

```
Web UI ──PUT──▶ FastAPI (update scope)
                  │
                  ├── Reconcile → ProfileAssignment rows
                  │
                  └── RabbitMQ ──▶ Device (profile.push.requested)
                  │
                  └── SSE ──────▶ SSE Server (external)
```

### Device check-in

```
Device ──POST──▶ /devices/{id}/check-in
                   │
                   ├── Recalculate assignments
                   ├── Dispatch latest revision (SSE push)
                   └── Return { "status": "ok" }
```

## RabbitMQ Exchange

- **Exchange**: `mdm.device.commands` (topic)
- **Routing key**: `device.<device_id>`
- **Events**: `profile.push.requested`, `profile.revoke.requested`, device commands

The consumer processes device-reported status updates (acknowledgement, completion, etc.).

## SSE Notification Payloads

**Profile assignment (group scope):**
```json
{
  "group_id": 1,
  "group_name": "Engineering",
  "profile": {
    "id": 1,
    "name": "Base Security Profile"
  }
}
```

**Profile push to device:**
```json
{
  "device_serial_number": "SN001",
  "device_name": "Device 1",
  "profile": {
    "id": 1,
    "name": "Enforce Encryption",
    "config": { "key": "value" }
  }
}
```
