# tMDM Control Backend

Backend service for MDM (Mobile Device Management) control plane. Built with FastAPI, async SQLAlchemy, MariaDB, and RabbitMQ.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Next.js FE │────▶│  FastAPI API │────▶│  SSE Server    │
│  (webhook)  │◀────│  (this app)  │     │  (external)    │
└─────────────┘     └──────┬───────┘     └────────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌──────────────┐
              │  MariaDB │  │  RabbitMQ    │────▶ Devices
              └──────────┘  └──────────────┘
```

- **API** — FastAPI async endpoints at `/api/v1/*` (see [API.md](API.md))
- **Database** — MariaDB via `aiomysql` + SQLAlchemy 2.0 async ORM
- **Messaging** — RabbitMQ (FastStream) for outbound profile/app/command push to devices; devices report status back via PUT endpoints
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
- RabbitMQ on `localhost:5672` (optional for unit tests; required in production for profile/app/command dispatch)

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
| `DB_URL` | `mysql+aiomysql://user:password@localhost:3306/mdm_control` | Database connection string |
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

Tests use an in-memory SQLite database with `aiosqlite`. RabbitMQ is not required — the FastStream broker is mocked and `AssignmentReconciler.request_recalculate_*` methods are patched to run synchronously.

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI app, lifespan, middleware, health check
│   ├── dependencies.py         # FastAPI dependency injection
│   ├── lifecycle.py            # App lifecycle (start/stop FastStream broker)
│   ├── webhook_client.py       # Next.js ISR revalidation helper
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
│   ├── domains/                # Domain modules (models, schemas, repos, services)
│   │   ├── shared/             # Scope value object, shared types
│   │   ├── profiles/           # Configuration profiles + assignments
│   │   ├── smart_groups/       # Dynamic device groups (criteria-based)
│   │   ├── static_groups/      # Explicit device groups
│   │   ├── devices/            # Device management
│   │   ├── commands/           # Device commands (lock, wipe, restart, etc.)
│   │   ├── mobile_apps/        # Mobile application distribution
│   │   ├── extension_attributes/  # Custom device metadata fields
│   │   ├── inventory_search/   # Saved device search queries
│   │   └── users/              # User management
│   ├── infra/                  # Infrastructure layer
│   │   ├── config/             # Pydantic settings from .env
│   │   ├── core/               # SQLAlchemy base, custom types, security
│   │   ├── common/             # Shared schemas (CamelModel, PaginatedResponse)
│   │   ├── messaging/          # FastStream broker, producer, schemas, reconciliation
│   │   ├── criteria/           # Smart group criteria evaluation
│   │   ├── reconciler/         # AssignmentReconciler (scope → assignment dispatch)
│   │   └── webhooks/           # Webhook helpers
│   ├── mock/
│   │   └── seed.py             # Database seeder
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
| `PUT` | `/devices/{id}/commands/{command_id}/status` | Update command status |

### Mobile Apps

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/mobile-apps` | List all mobile apps |
| `GET` | `/mobile-apps/{id}` | Get app by ID |
| `POST` | `/mobile-apps` | Create a mobile app |
| `PUT` | `/mobile-apps/{id}` | Update a mobile app |
| `DELETE` | `/mobile-apps/{id}` | Delete a mobile app |
| `GET` | `/mobile-apps/{id}/assignments` | List mobile app assignments |
| `PUT` | `/mobile-apps/{id}/assignments/{device_id}/status` | Update app assignment status |

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

Group scope changes and device updates trigger the `AssignmentReconciler`, which:

1. Recalculates desired state (PRESENT/ABSENT) for all affected (profile, device) pairs
2. Writes new assignment revision rows (append-only)
3. Publishes profile push/revoke events to RabbitMQ (`tmdm.sse.messages` exchange)
4. During device check-in, dispatches the latest revision directly

### Group scope change

```
Web UI ──PUT──▶ FastAPI (update scope)
                  │
                  ├── Reconcile → ProfileAssignment rows
                  │
                  └── RabbitMQ ──▶ Device (profile.push)
```

### Device check-in

```
Device ──POST──▶ /devices/{id}/check-in
                   │
                   ├── Recalculate assignments (synchronous)
                   ├── Dispatch latest revision via RabbitMQ
                   └── Return { "status": "ok" }
```

### Device status reporting

Devices report command and assignment status back via PUT endpoints:

- `PUT /devices/{id}/commands/{command_id}/status` — command acknowledgement, completion, or failure
- `PUT /profiles/{id}/assignments/{device_id}/status` — profile assignment status
- `PUT /mobile-apps/{id}/assignments/{device_id}/status` — mobile app assignment status

## RabbitMQ Exchange

- **Exchange**: `tmdm.sse.messages` (topic, durable)
- **Routing key**: device serial number
- **Message schema**: `kind` field discriminates message type (`profile.push`, `profile.revoke`, `mobile_app.push`, `mobile_app.revoke`, `device.command`)
- **Required fields**: `serial_number`, plus per-type fields (`assignment_id`, `profile_version` / `app_version`, etc.)
- **Reconciliation queue**: separate queue for async recalculation requests (`profile.recalculate`, `mobile_app.recalculate`)

There is no inbound consumer — devices report status via PUT endpoints.

## SSE Notification Payloads

**Profile push to device:**
```json
{
  "kind": "profile.push",
  "serial_number": "SN001",
  "profile_id": 1,
  "profile_config": { "key": "value" },
  "profile_version": 2,
  "assignment_id": 42
}
```

**Device command:**
```json
{
  "kind": "device.command",
  "serial_number": "SN001",
  "command_id": 7,
  "command_type": "LOCK",
  "parameters": {}
}
```
