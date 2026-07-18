# API Reference

Base URL: `/api/v1`

## Devices

| Method | Path | Description |
|---|---|---|
| `GET` | `/devices` | List all devices (paginated) |
| `GET` | `/devices/{device_id}` | Get device by ID |
| `POST` | `/devices/search` | Search devices by criteria |
| `POST` | `/devices/{device_id}/policy` | Assign policy to device (Kafka event) |

### `GET /devices`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip (min 0) |
| `limit` | int | `100` | Max items to return (max 5000) |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "MacBook Pro",
      "serial": "SN001",
      "owner": "Alice",
      "os_version": "15.0",
      "status": "Online",
      "compliance": "Compliant",
      "last_seen": "2025-01-01T00:00:00Z",
      "battery_level": 85,
      "total_storage": 512,
      "available_storage": 200,
      "total_memory": 16,
      "available_memory": 8,
      "cpu_usage": 45.2,
      "last_boot": "2025-01-01T00:00:00Z",
      "signal_strength": -65,
      "policies": ["Enforce Encryption"]
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 100
}
```

### `GET /devices/{device_id}`

**Path parameters:** `device_id` (int)

**Response `200`:** Single `DeviceResponse` object (see above)

**Response `404`:** `{"detail": "Device not found"}

### `POST /inventory-search/execute`

**Request body (`InventorySearchExecuteRequest`):**

```json
{
  "conjunction": "AND",
  "criteria": [
    {"field": "connection_status", "operator": "is", "type": "STRING", "value": "Online"},
    {"field": "battery_status", "operator": "greaterThan", "type": "NUMBER", "value": "50"}
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `conjunction` | string | No | `"AND"` (default) or `"OR"` |
| `criteria` | list | Yes | Non-empty list of `Criteria` objects |

**Response `200`:** Array of `DeviceResponse` objects.

### `POST /devices/{device_id}/policy`

**Path parameters:** `device_id` (int)

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `policy_id` | int | Yes | Policy ID to assign |

**Response `200`:** Updated `DeviceResponse` object.

**Response `404`:** `{"detail": "Device not found"}`

## Policies

| Method | Path | Description |
|---|---|---|
| `GET` | `/policies` | List all policies (paginated) |
| `GET` | `/policies/{policy_id}` | Get policy by ID |

### `GET /policies`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip (min 0) |
| `limit` | int | `100` | Max items to return (max 1000) |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Enforce Encryption",
      "description": "Requires disk encryption",
      "config": {},
      "rollout_state": "Active"
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 100
}
```

### `GET /policies/{policy_id}`

**Path parameters:** `policy_id` (int)

**Response `200`:** Single `PolicyResponse` object.

**Response `404`:** `{"detail": "Policy not found"}`

## Smart Groups

| Method | Path | Description |
|---|---|---|
| `GET` | `/smart-groups` | List all smart groups (paginated) |
| `GET` | `/smart-groups/{group_id}` | Get group by ID |
| `POST` | `/smart-groups` | Create a smart group (`is_smart=true`) |
| `PUT` | `/smart-groups/{group_id}` | Update a group |
| `DELETE` | `/smart-groups/{group_id}` | Delete a group |

### `GET /smart-groups`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip (min 0) |
| `limit` | int | `100` | Max items to return (max 1000) |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Engineering",
      "description": "Engineering department",
      "is_smart": true,
      "criteria": { "os": "macOS" },
      "display_columns": ["name", "os_version"]
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 100
}
```

### `GET /smart-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Response `200`:** Single `GroupResponse` object.

**Response `404`:** `{"detail": "Group not found"}`

### `POST /smart-groups`

**Request body:**

```json
{
  "name": "Engineering",
  "description": "Engineering department",
  "criteria": { "os": "macOS" },
  "display_columns": ["name", "os_version"]
}
```

`name` required, rest optional. `is_smart` is set to `true` automatically.

**Response `201`:** Created `GroupResponse` object.

### `PUT /smart-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Request body** (at least one field):

```json
{
  "name": "Engineering Team",
  "description": "Updated description"
}
```

**Response `200`:** Updated `GroupResponse` object.

**Response `400`:** `{"detail": "No fields to update"}`

**Response `404`:** `{"detail": "Group not found"}`

### `DELETE /smart-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Response `200`:** `{"detail": "Group deleted"}`

**Response `404`:** `{"detail": "Group not found"}`

## Static Groups

| Method | Path | Description |
|---|---|---|
| `GET` | `/static-groups` | List all static groups (paginated) |
| `GET` | `/static-groups/{group_id}` | Get group by ID |
| `POST` | `/static-groups` | Create a static group (`is_smart=false`) |
| `PUT` | `/static-groups/{group_id}` | Update a group |
| `DELETE` | `/static-groups/{group_id}` | Delete a group |

### `GET /static-groups`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip (min 0) |
| `limit` | int | `100` | Max items to return (max 1000) |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 2,
      "name": "Marketing",
      "description": "Marketing department",
      "is_smart": false
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 100
}
```

### `GET /static-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Response `200`:** Single `GroupResponse` object.

**Response `404`:** `{"detail": "Group not found"}`

### `POST /static-groups`

**Request body:**

```json
{
  "name": "Marketing",
  "description": "Marketing department"
}
```

`name` required, `description` optional. `is_smart` is set to `false` automatically.

**Response `201`:** Created `GroupResponse` object.

### `PUT /static-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Request body** (at least one field):

```json
{
  "name": "Marketing Team",
  "description": "Updated description"
}
```

**Response `200`:** Updated `GroupResponse` object.

**Response `400`:** `{"detail": "No fields to update"}`

**Response `404`:** `{"detail": "Group not found"}`

### `DELETE /static-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Response `200`:** `{"detail": "Group deleted"}`

**Response `404`:** `{"detail": "Group not found"}`

### Policy Assignment (both Smart and Static)

| Method | Path | Description |
|---|---|---|
| `POST` | `/{type}/groups/{group_id}/policies` | Assign a policy to a group |

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `policy_id` | int | Yes | Policy ID to assign |

**Response `201`:** Updated `GroupResponse` object.

**Response `404`:** `{"detail": "Group or policy not found"}`

## Users

| Method | Path | Description |
|---|---|---|
| `GET` | `/users` | List all users (paginated) |
| `GET` | `/users/{user_id}` | Get user by ID |
| `GET` | `/users/by-email/{email}` | Get user by email |
| `PUT` | `/users/{user_id}/role` | Update user role |

### `GET /users`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip (min 0) |
| `limit` | int | `100` | Max items to return (max 1000) |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "username": "alice",
      "email": "alice@example.com",
      "role_id": 1
    }
  ],
  "total": 10,
  "skip": 0,
  "limit": 100
}
```

### `GET /users/{user_id}`

**Path parameters:** `user_id` (int)

**Response `200`:** Single `UserResponse` object.

**Response `404`:** `{"detail": "User not found"}`

### `GET /users/by-email/{email}`

**Path parameters:** `email` (str)

**Response `200`:** Single `UserResponse` object.

**Response `404`:** `{"detail": "User not found"}`

### `PUT /users/{user_id}/role`

**Path parameters:** `user_id` (int)

**Query parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `role_id` | int | Yes | New role ID |

**Response `200`:** Updated `UserResponse` object.

**Response `404`:** `{"detail": "User not found"}`

## Roles

| Method | Path | Description |
|---|---|---|
| `GET` | `/roles` | List all roles (paginated) |
| `GET` | `/roles/{role_id}` | Get role by ID |

### `GET /roles`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip (min 0) |
| `limit` | int | `100` | Max items to return (max 1000) |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Admin",
      "description": "Administrator role"
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 100
}
```

### `GET /roles/{role_id}`

**Path parameters:** `role_id` (int)

**Response `200`:** Single `RoleResponse` object.

**Response `404`:** `{"detail": "Role not found"}`

## Metrics

| Method | Path | Description |
|---|---|---|
| `GET` | `/metrics/fleet` | Fleet overview metrics |

### `GET /metrics/fleet`

**Response `200`:**

```json
{
  "total_devices": 42,
  "online_devices": 38,
  "pending_policies": 3
}
```

## Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Database and Kafka health check |

### `GET /health`

**Response `200`:**

```json
{
  "status": "ok",
  "database": "ok",
  "kafka": "ok"
}
```

**Response `503`:**

```json
{
  "status": "error",
  "database": "error",
  "kafka": "disconnected"
}
```

## Pagination

All list endpoints return:

```json
{
  "items": [...],
  "total": <int>,
  "skip": <int>,
  "limit": <int>
}
```

- `skip` — number of records skipped (default 0)
- `limit` — max records returned (capped at 1000, 5000 for devices)
- `total` — total matching records in the database

## Common Responses

| Status | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `400` | Bad request — missing or invalid parameters |
| `404` | Resource not found |
| `503` | Service unavailable (health check) |
