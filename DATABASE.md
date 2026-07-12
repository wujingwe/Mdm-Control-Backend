# Database Schema Reference

MariaDB backend with 9 tables across 7 domain modules. All tables extend `Base` from `app/base.py`.

---

## Tables

### 1. `users`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| email | VARCHAR(255) | UNIQUE | |
| name | VARCHAR(100) | | |
| password_hash | VARCHAR(255) | nullable | |
| permissions | JSON | NOT NULL | `["viewer"]` |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow |
| last_login | DATETIME | nullable | |

---

### 2. `devices`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | | |
| serial_number | VARCHAR(30) | UNIQUE | |
| os_version | VARCHAR(20) | | |
| connection_status | VARCHAR(20) | NOT NULL, INDEX | |
| enrollment_status | VARCHAR(20) | NOT NULL, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL, onupdate | utcnow |
| last_enrolled_at | DATETIME | NOT NULL | utcnow |
| battery_status | INT | nullable | |
| total_storage | INT | nullable | |
| available_storage | INT | nullable | |
| total_memory | INT | nullable | |
| available_memory | INT | nullable | |
| network | JSON (custom) | nullable | |
| certificates | JSON (custom) | nullable | |

---

### 3. `smart_groups`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | | |
| description | VARCHAR(500) | nullable | |
| created_by | INT | FK → `users.id`, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow |
| criteria | JSON | nullable | |

---

### 4. `static_groups`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | | |
| description | VARCHAR(500) | nullable | |
| created_by | INT | FK → `users.id`, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow |

**Relationships:**
- `devices` — M2M via `static_group_devices` (CASCADE, FK on `devices.id`)

---

### 5. `profiles`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE | |
| description | TEXT | nullable | |
| version | INT | NOT NULL | 1 |
| settings | JSON | NOT NULL | `{}` |
| created_by | INT | FK → `users.id`, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow |

**Relationships:**
- `profile_scope` — 1:N via `profile_scope.profile_id` (CASCADE on delete)
- `profile_assignments` — 1:N via `profile_assignments.profile_id` (CASCADE on delete)

---

### 6. `extension_attributes`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE | |
| description | TEXT | nullable | |
| data_type | VARCHAR(20) | NOT NULL | |
| input_type | VARCHAR(20) | NOT NULL | |
| popup_choices | JSON | nullable | |
| created_by | INT | FK → `users.id`, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow |

**Enum values:**
- `data_type`: `string`, `integer`, `date`
- `input_type`: `Text field`, `Pop-up menu`

---

### 7. `inventory_searches`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| name | VARCHAR(100) | UNIQUE | |
| description | TEXT | nullable | |
| criteria | JSON | nullable | |
| created_by | INT | FK → `users.id`, INDEX | |
| created_at | DATETIME | NOT NULL | utcnow |
| updated_at | DATETIME | NOT NULL | utcnow |

---

## Junction / Association Tables

### 8. `static_group_devices`

| Column | Type | Constraints |
|---|---|---|
| static_group_id | INT | PK, FK → `static_groups.id` (CASCADE) |
| device_id | INT | PK, FK → `devices.id` (CASCADE) |

---

### 9. `profile_scope`

| Column | Type | Constraints | Default |
|---|---|---|---|
| id | INT | PK, autoincrement | |
| profile_id | INT | FK → `profiles.id` (CASCADE), INDEX | |
| target_type | VARCHAR(20) | NOT NULL | |
| target_id | INT | nullable | |

**Unique constraint:** `(profile_id, target_type, target_id)`

**Enum values for `target_type`:** `ALL_DEVICES`, `SMART_GROUP`, `STATIC_GROUP`, `DEVICE`

When `target_type` is `ALL_DEVICES`, `target_id` is NULL.
When `target_type` is `SMART_GROUP` or `STATIC_GROUP`, `target_id` references the group's `id`.

---

### 10. `profile_assignments`

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

**Enum values for `source`:** `DIRECT`, `SMART_GROUP`, `STATIC_GROUP`
**Enum values for `status`:** `PENDING`, `APPLIED`, `FAILED`, `REVOKED`, `REMOVED`

> **Note:** `source_id` is a polymorphic FK — it references `smart_groups.id` when `source='SMART_GROUP'`, or `static_groups.id` when `source='STATIC_GROUP'`. No DB-level FK constraint because the target table varies.

---

## Relationship Diagram (Text)

```
┌──────────────┐       ┌────────────────────────┐
│  static_groups│──────<│  static_group_devices  │
│              │       │  CASCADE on both FKs    │
└──────────────┘       └────────────────────────┘
       │                         │
       │                         v
       │                  ┌──────────┐
       │                  │  devices │
       │                  └──────────┘
       │                         ^
       │                         │
       │       ┌──────────────────────────┐
       └──────<│  profile_assignments     │
               │  CASCADE on both FKs     │
               └──────────────────────────┘
                        │              │
                        v              v
                 ┌──────────┐   ┌──────────┐
                 │ profiles │   │  devices │
                 └──────────┘   └──────────┘
                        ^
                        │
               ┌────────────────────┐
               │    profile_scope   │
               │    CASCADE, UNIQUE │
               └────────────────────┘

┌──────────────┐
│ smart_groups │────────────────────────┐
└──────────────┘                        │
                                        v
                               ┌─────────────────┐
                               │ profile_scope    │
                               │ (as target)      │
                               └─────────────────┘

┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────────┐
│ extension_attributes│  │ inventory_searches│  │       users         │
│ FK → users.id       │  │ FK → users.id     │  │                     │
└─────────────────────┘  └──────────────────┘  └─────────────────────┘
```

## Relationships (Text)

```
static_groups      ──M2M──  devices           (via static_group_devices, CASCADE both, FK on devices.id)
profiles           ──1:N──  profile_scope     (profile_id, CASCADE on delete, UNIQUE on profile+type+id)
profiles           ──1:N──  profile_assignments (profile_id, CASCADE on delete)
devices            ──1:N──  profile_assignments (device_id, CASCADE on delete)
smart_groups       ──N:1──  users             (created_by FK)
static_groups      ──N:1──  users             (created_by FK)
profiles           ──N:1──  users             (created_by FK)
extension_attributes ──N:1── users            (created_by FK)
inventory_searches ──N:1──  users             (created_by FK)
```

**Polymorphic references (no DB-level FK):**
- `profile_assignments.source_id` → `smart_groups.id` or `static_groups.id` (depends on `source`)

---

## Indexes

| Table | Column(s) | Purpose |
|---|---|---|
| devices | connection_status | Filter by online/offline status |
| devices | enrollment_status | Filter by compliance state |
| smart_groups | created_by | Query groups by creator |
| static_groups | created_by | Query groups by creator |
| profiles | created_by | Query profiles by creator |
| extension_attributes | created_by | Query attributes by creator |
| inventory_searches | created_by | Query searches by creator |
| profile_scope | profile_id | Join/filter scope by profile |
| profile_assignments | profile_id | Join/filter assignments by profile |
| profile_assignments | device_id | Join/filter assignments by device |

---

## Schema Design Notes

### What's Done Well

1. **Clean domain separation** — Each domain owns its models, with junction tables in the same module.
2. **JSON for nested/flexible data** — `network`, `certificates`, `criteria`, `settings`, `popup_choices` use JSON appropriately for structured data that doesn't need relational querying.
3. **Profile scope is polymorphic** — `target_type` + `target_id` pattern supports ALL_DEVICES, group, and device targeting without separate columns.
4. **Profile assignment tracks lineage** — `source` + `source_id` records whether an assignment came from DIRECT, SMART_GROUP, or STATIC_GROUP origin, enabling proper revocation.
5. **Unique constraints on identity columns** — `users.email`, `devices.serial_number`, `profiles.name`, `extension_attributes.name`, `inventory_searches.name` are all UNIQUE.
6. **Cascade deletes everywhere** — All junction tables use `ON DELETE CASCADE`. Profile children cascade. Device assignments cascade.
7. **Consistent FK convention** — All junction tables FK to the parent table's `id` column (including `static_group_devices` which was migrated from `serial_number` to `id`).
8. **Referential integrity on `created_by`** — All creator columns FK to `users.id`, preventing orphaned records.
9. **Indexed foreign keys** — Non-PK FK columns are indexed for query performance.
10. **Unique constraint on `profile_scope`** — Prevents duplicate scope entries per profile.
11. **Profile version tracking** — `profiles.version` column tracks configuration version for deployment tracking.

### Known Limitations

1. **`profile_assignments.source_id` has no DB-level FK** — Polymorphic reference (could point to `smart_groups.id` or `static_groups.id` depending on `source`). Application-level integrity only.
2. **`devices.network` and `devices.certificates` are JSON** — No FK, no indexing, no validation at the DB level. Acceptable for per-device metadata.
3. **`extension_attributes.popup_choices`** — JSON array only relevant when `input_type` is "Pop-up menu". No DB-level constraint enforcing this.
