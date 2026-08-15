# Database Schema Reference

## Tables

### Domain Tables
| # | Table | Model | Domain |
|---|---|---|---|
| 1 | `users` | `User` | users |
| 2 | `devices` | `Device` | devices |
| 3 | `smart_groups` | `SmartGroup` | smart_groups |
| 4 | `static_groups` | `StaticGroup` | static_groups |
| 5 | `profiles` | `Profile` | profiles |
| 6 | `extension_attributes` | `ExtensionAttribute` | extension_attributes |
| 7 | `inventory_searches` | `InventorySearch` | inventory_search |
| 8 | `commands` | `Command` | commands |

### Junction / Association Tables
| # | Table | Model | Domain |
|---|---|---|---|
| 9 | `device_extension_attribute_values` | `DeviceExtensionAttribute` | devices |
| 10 | `static_group_devices` | `StaticGroupDevice` | static_groups |
| 11 | `profile_scope` | `ProfileScope` | profiles |
| 12 | `profile_assignments` | `ProfileAssignment` | profiles |

MariaDB backend with 12 tables across 8 domain modules. All tables extend `Base` from `app/base.py`.

---

## Tables

### 1. `users`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| email | VARCHAR(255) | UNIQUE, NOT NULL | |
| name | VARCHAR(100) | NOT NULL | |
| password_hash | VARCHAR(255) | nullable | |
| permissions | JSON (PermissionListType) | NOT NULL | `["viewer"]` |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |
| last_login | DATETIME | nullable | |

---

### 2. `devices`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | NOT NULL | |
| serial_number | VARCHAR(30) | UNIQUE, NOT NULL | |
| os_version | VARCHAR(20) | NOT NULL, INDEX | |
| connection_status | VARCHAR(20) | NOT NULL, INDEX | |
| enrollment_status | VARCHAR(20) | NOT NULL, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |
| last_enrolled_at | DATETIME | NOT NULL | utcnow |
| battery_status | INT | nullable | |
| total_storage | INT | nullable | |
| available_storage | INT | nullable | |
| total_memory | INT | nullable | |
| available_memory | INT | nullable | |
| network | JSON (NetworkInfoType) | nullable | |
| certificates | JSON (CertificateListType) | nullable | |

**Enum values:**
- `connection_status`: `Online`, `Offline`, `Pending`
- `enrollment_status`: `Compliant`, `Non-compliant`, `Needs attention`, `Enrolled`, `Pending`, `Unknown`

**Relationships:**
- `extension_attributes` — 1:N via `device_extension_attribute_values.device_id` (viewonly)
- `profiles` — M2M via `profile_assignments` (viewonly)

---

### 3. `smart_groups`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE, NOT NULL | |
| description | TEXT | nullable | |
| created_by | INT | FK → `users.id` (SET NULL), nullable, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |
| criteria | JSON | nullable | |

**Relationships:**
- `creator` — N:1 → `users` (viewonly)

> **Note:** `criteria` is a JSON array of `Criteria` objects, each with: `field`, `operator`, `type`, `value`, `left_parentheses`, `right_parentheses`. Criteria is a Pydantic schema (not a DB table) — see `app/criteria/schemas.py`.

---

### 4. `static_groups`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE, NOT NULL | |
| description | TEXT | nullable | |
| created_by | INT | FK → `users.id` (SET NULL), nullable, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |

**Relationships:**
- `creator` — N:1 → `users` (viewonly)
- `devices` — M2M via `static_group_devices` (joined on `Device.serial_number`)

---

### 5. `profiles`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE, NOT NULL | |
| description | TEXT | nullable | |
| version | INT | NOT NULL | 1 |
| settings | JSON | NOT NULL | `{}` |
| created_by | INT | FK → `users.id` (SET NULL), nullable, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |

**Relationships:**
- `creator` — N:1 → `users` (viewonly)
- `scopes` — 1:N via `profile_scope.profile_id` (CASCADE)
- `assignments` — 1:N via `profile_assignments.profile_id` (CASCADE)

---

### 6. `extension_attributes`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE, NOT NULL | |
| description | TEXT | nullable | |
| data_type | VARCHAR(20) | NOT NULL | |
| input_type | VARCHAR(20) | NOT NULL | |
| popup_choices | JSON | nullable | |
| created_by | INT | FK → `users.id` (SET NULL), nullable, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |

**Enum values:**
- `data_type`: `string`, `integer`, `date`
- `input_type`: `Text field`, `Pop-up menu`

**Relationships:**
- `creator` — N:1 → `users` (viewonly)

---

### 7. `inventory_searches`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE, NOT NULL | |
| description | TEXT | nullable | |
| criteria | JSON | nullable | |
| created_by | INT | FK → `users.id` (SET NULL), nullable, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow, onupdate |

**Relationships:**
- `creator` — N:1 → `users` (viewonly)

> **Note:** `criteria` uses the same `Criteria` schema as `smart_groups` — see `app/criteria/schemas.py`.

---

### 8. `commands`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| device_id | INT | FK → `devices.id` (CASCADE), NOT NULL, INDEX | |
| command_type | VARCHAR(30) | NOT NULL, INDEX | |
| parameters | JSON | nullable | |
| status | VARCHAR(20) | NOT NULL, INDEX | `PENDING` |
| result_message | TEXT | nullable | |
| created_by | INT | FK → `users.id` (SET NULL), nullable | |
| created_at | DATETIME | NOT NULL, INDEX | utcnow |
| sent_at | DATETIME | nullable | |
| acknowledged_at | DATETIME | nullable | |
| completed_at | DATETIME | nullable | |
| rabbitmq_message_id | VARCHAR(36) | nullable | |

**Enum values:**
- `command_type`: `CHECK_IN`, `UPDATE_INVENTORY`, `LOCK`, `UNLOCK`, `WIPE`, `RESTART`, `SHUTDOWN`, `LOST_MODE`
- `status`: `PENDING`, `SENT`, `ACKNOWLEDGED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED`

**Status lifecycle:** `PENDING` → `SENT` → `ACKNOWLEDGED` → `IN_PROGRESS` → `COMPLETED`/`FAILED`; `CANCELLED` reachable from `PENDING` or `SENT`.

**Relationships:**
- `device` — N:1 → `devices` (viewonly)

---

## Junction / Association Tables

### 9. `device_extension_attribute_values`

| Column | Type | Constraints |
|---|---|---|
| id | INT | PK, autoincrement |
| device_id | INT | FK → `devices.id` (CASCADE), NOT NULL, INDEX |
| extension_attribute_id | INT | FK → `extension_attributes.id` (CASCADE), NOT NULL |
| extension_attribute_name | VARCHAR(100) | NOT NULL |
| value | TEXT | NOT NULL |
| created_at | DATETIME | NOT NULL, utcnow |
| updated_at | DATETIME | NOT NULL, utcnow, onupdate |

**Unique constraint:** `(device_id, extension_attribute_id)`

---

### 10. `static_group_devices`

| Column | Type | Constraints |
|---|---|---|
| static_group_id | INT | PK, FK → `static_groups.id` (CASCADE) |
| device_serial_number | VARCHAR | PK, FK → `devices.serial_number` (CASCADE) |
| created_at | DATETIME | NOT NULL, utcnow |

> **Note:** FK on `devices.serial_number` (not `devices.id`).

---

### 11. `profile_scope`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| profile_id | INT | FK → `profiles.id` (CASCADE), INDEX | |
| target_type | VARCHAR(20) | NOT NULL | |
| target_id | INT | NOT NULL | 0 |

**Unique constraint:** `(profile_id, target_type, target_id)`

**Enum values for `target_type`:** `ALL_DEVICES`, `SMART_GROUP`, `STATIC_GROUP`, `DEVICE`

> When `target_type` is `ALL_DEVICES`, `target_id` is `0`. When `target_type` is `SMART_GROUP` or `STATIC_GROUP`, `target_id` references the group's `id`. When `target_type` is `DEVICE`, `target_id` references the device's `id`.

---

### 12. `profile_assignments`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| profile_id | INT | FK → `profiles.id` (CASCADE), INDEX | |
| device_id | INT | FK → `devices.id` (CASCADE), INDEX | |
| source | VARCHAR(20) | NOT NULL | |
| source_id | INT | nullable | |
| status | VARCHAR(20) | NOT NULL | `PENDING` |
| profile_version | INT | NOT NULL | 1 |
| assigned_at | DATETIME | NOT NULL | utcnow |
| applied_at | DATETIME | nullable | |
| revoked_at | DATETIME | nullable | |

**Unique constraint:** `(profile_id, device_id)`

**Enum values for `source`:** `DIRECT`, `SMART_GROUP`, `STATIC_GROUP`, `ALL_DEVICES`
**Enum values for `status`:** `PENDING`, `APPLIED`, `FAILED`, `REVOKED`, `REMOVED`

> **Note:** `source_id` is a polymorphic FK — it references `smart_groups.id` when `source='SMART_GROUP'`, or `static_groups.id` when `source='STATIC_GROUP'`. No DB-level FK constraint because the target table varies.

---

## Relationship Diagram (Text)

```
┌──────────────┐       ┌───────────────────────────────┐
│ static_groups│──────<│     static_group_devices      │
│              │       │  CASCADE, FK on serial_number │
└──────────────┘       └───────────────────────────────┘
       │                          │
       │                          v
       │                   ┌──────────┐
       │                   │  devices │
       │                   └──────────┘
       │                  ^  ^  ^     ^
       │                  │  │  │     │
       │  ┌───────────────┘  │  │     └──────────────────────────┐
       │  │                  │  │                                │
       │  │  ┌───────────────┘  │    ┌───────────────────────┐   │
       │  │  │                  │    │  commands             │   │
       │  │  │                  │    │  FK → devices.id      │   │
       │  │  │                  │    └───────────────────────┘   │
       │  │  │                  │                                │
       │  │  │       ┌──────────────────────────┐    ┌───────────┴─────────────┐
       │  │  │       │   profile_assignments    │    │ device_ext_attr_values  │
       │  └──┼──────>│   CASCADE on both FKs    │<───│ CASCADE on both FKs     │
       │     │       └──────────────────────────┘    └─────────────────────────┘
       │     │                │              │                      │
       │     │                v              v                      v
       │     │         ┌──────────┐   ┌──────────┐    ┌───────────────────────┐
       │     │         │ profiles │   │          │    │ extension_attributes  │
       │     │         └──────────┘   └──────────┘    │ FK → users.id         │
       │     │                ^                       └───────────────────────┘
       │     │                │
       │     │       ┌────────────────────┐
       │     └──────>│    profile_scope   │
       │             │    CASCADE, UNIQUE │
       │             └────────────────────┘
       │
       │      ┌──────────────────┐  ┌─────────────────────┐
       └─────<│   smart_groups   │  │   inventory_searches│
              │ FK → users.id    │  │   FK → users.id     │
              └──────────────────┘  └─────────────────────┘

              ┌──────────┐
              │  users   │
              └──────────┘
```

## Relationships (Text)

```
static_groups         ──M2M──  devices                  (via static_group_devices, FK on serial_number)
profiles              ──1:N──  profile_scope            (profile_id, CASCADE)
profiles              ──1:N──  profile_assignments      (profile_id, CASCADE)
devices               ──1:N──  profile_assignments      (device_id, CASCADE)
devices               ──1:N──  commands                 (device_id, CASCADE)
devices               ──1:N──  device_extension_attribute_values (device_id, CASCADE)
extension_attributes  ──1:N──  device_extension_attribute_values (extension_attribute_id, CASCADE)
smart_groups          ──N:1──  users                     (created_by FK, SET NULL)
static_groups         ──N:1──  users                     (created_by FK, SET NULL)
profiles              ──N:1──  users                     (created_by FK, SET NULL)
extension_attributes  ──N:1──  users                     (created_by FK, SET NULL)
inventory_searches    ──N:1──  users                     (created_by FK, SET NULL)
commands              ──N:1──  users                     (created_by FK, SET NULL)
```

**Polymorphic references (no DB-level FK):**
- `profile_assignments.source_id` → `smart_groups.id` or `static_groups.id` (depends on `source`)

---

## Indexes

| Table | Column(s) | Purpose |
|---|---|---|
| devices | os_version | Filter by OS version |
| devices | connection_status | Filter by online/offline status |
| devices | enrollment_status | Filter by compliance state |
| smart_groups | created_by | Query groups by creator |
| profiles | created_by | Query profiles by creator |
| extension_attributes | created_by | Query attributes by creator |
| inventory_searches | created_by | Query searches by creator |
| profile_scope | profile_id | Join/filter scope by profile |
| profile_assignments | profile_id | Join/filter assignments by profile |
| profile_assignments | device_id | Join/filter assignments by device |
| commands | device_id | Join/filter commands by device |
| commands | status | Filter by command status |
| commands | command_type | Filter by command type |
| commands | created_at | Sort/filter by creation time |
| device_extension_attribute_values | device_id | Join/filter by device |

---

## Schema Design Notes

### What's Done Well

1. **Clean domain separation** — Each domain owns its models, with junction tables in the same module.
2. **JSON for nested/flexible data** — `network`, `certificates`, `criteria`, `settings`, `popup_choices` use JSON appropriately for structured data that doesn't need relational querying.
3. **Profile scope is polymorphic** — `target_type` + `target_id` pattern supports ALL_DEVICES, group, and device targeting without separate columns.
4. **Profile assignment tracks lineage** — `source` + `source_id` records whether an assignment came from DIRECT, SMART_GROUP, STATIC_GROUP, or ALL_DEVICES origin, enabling proper revocation.
5. **Unique constraints on identity columns** — `users.email`, `devices.serial_number`, `profiles.name`, `extension_attributes.name`, `smart_groups.name`, `static_groups.name`, `inventory_searches.name` are all UNIQUE.
6. **Cascade deletes everywhere** — All junction tables use `ON DELETE CASCADE`. Profile children cascade. Device assignments cascade.
7. **Consistent FK convention** — All `created_by` columns use `ON DELETE SET NULL` with nullable FK. Junction tables use `ON DELETE CASCADE`.
8. **Referential integrity on `created_by`** — All creator columns FK to `users.id`, preventing orphaned records while allowing user deletion.
9. **Indexed foreign keys** — Non-PK FK columns are indexed for query performance.
10. **Unique constraint on `profile_scope`** — Prevents duplicate scope entries per profile.
11. **Profile version tracking** — `profiles.version` column tracks configuration version for deployment tracking.

### Known Limitations

1. **`profile_assignments.source_id` has no DB-level FK** — Polymorphic reference (could point to `smart_groups.id` or `static_groups.id` depending on `source`). Application-level integrity only.
2. **`devices.network` and `devices.certificates` are JSON** — No FK, no indexing, no validation at the DB level. Acceptable for per-device metadata.
3. **`extension_attributes.popup_choices`** — JSON array only relevant when `input_type` is "Pop-up menu". No DB-level constraint enforcing this.
4. **`static_group_devices` FK on `serial_number`** — Most junction tables FK on `id`, but this table uses `devices.serial_number` to support device replacement without updating junction rows.
