# API Reference

Base URL: `/api/v1`

## Devices

| Method | Path | Description |
|---|---|---|
| `GET` | `/devices` | List all devices (paginated) |
| `GET` | `/devices/{device_id}` | Get device by ID |
| `PUT` | `/devices/{device_id}` | Update a device (triggers reconciler) |
| `POST` | `/devices/{device_id}/check-in` | Device check-in (recalculate + dispatch) |
| `GET` | `/devices/{device_id}/commands` | List device commands |
| `GET` | `/devices/{device_id}/commands/{command_id}` | Get a command |
| `POST` | `/devices/{device_id}/commands` | Execute a command on a device |

### `GET /devices`

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
      "name": "Device 1",
      "serialNumber": "SN001",
      "osVersion": "15.0",
      "connectionStatus": "Connected",
      "status": "Enrolled",
      "batteryStatus": 85,
      "totalStorage": 512,
      "availableStorage": 200,
      "totalMemory": 16,
      "availableMemory": 8,
      "network": null,
      "certificates": null,
      "extensionAttributeValues": null,
      "lastEnrolledAt": "2025-01-01T00:00:00Z",
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 100
}
```

### `GET /devices/{device_id}`

**Path parameters:** `device_id` (int)

**Response `200`:** Single `DeviceResponse` object (see list response)

**Response `404`:** `{"detail": "Device not found"}`

### `PUT /devices/{device_id}`

**Path parameters:** `device_id` (int)

**Request body** (partial — at least one field):

```json
{
  "connectionStatus": "Disconnected",
  "batteryStatus": 72,
  "totalStorage": 512
}
```

Triggers `ProfileAssignmentReconciler` recalculation when certain fields change (`connectionStatus`, `status`, `osVersion`, `serialNumber`, `name`, battery/storage/memory fields, `extensionAttributeValues`).

**Response `200`:** Updated `DeviceResponse` object.

**Response `404`:** `{"detail": "Device not found"}`

### `POST /devices/{device_id}/check-in`

**Path parameters:** `device_id` (int)

Recalculates desired state for all profiles, then dispatches the consolidated latest revision to the device via RabbitMQ.

**Response `200`:** `{"status": "ok"}`

**Response `404`:** `{"detail": "Device not found"}`

### `POST /devices/{device_id}/commands`

**Path parameters:** `device_id` (int)

**Request body:**

```json
{
  "commandType": "LOCK"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `commandType` | string | Yes | One of `CHECK_IN`, `LOCK`, `UNLOCK`, `WIPE`, `RESTART`, `SHUTDOWN` |

**Response `201`:**

```json
{
  "id": 1,
  "deviceId": 1,
  "commandType": "LOCK",
  "status": "PENDING",
  "createdBy": 1,
  "createdAt": "2025-01-01T00:00:00Z",
  "sentAt": null,
  "acknowledgedAt": null,
  "completedAt": null,
  "resultMessage": null,
  "rabbitmqMessageId": null
}
```

**Response `404`:** `{"detail": "Device not found"}`

### `GET /devices/{device_id}/commands`

**Path parameters:** `device_id` (int)

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip |
| `limit` | int | `50` | Max items to return (max 100) |

**Response `200`:** Paginated list of `CommandResponse` objects.

### `GET /devices/{device_id}/commands/{command_id}`

**Path parameters:** `device_id` (int), `command_id` (int)

**Response `200`:** Single `CommandResponse` object.

**Response `404`:** `{"detail": "Command not found"}`

## Profiles

| Method | Path | Description |
|---|---|---|
| `GET` | `/profiles` | List all profiles (paginated) |
| `GET` | `/profiles/{profile_id}` | Get profile by ID |
| `POST` | `/profiles` | Create a profile |
| `PUT` | `/profiles/{profile_id}` | Update a profile |
| `DELETE` | `/profiles/{profile_id}` | Delete a profile (scope must be empty) |
| `GET` | `/profiles/{profile_id}/assignments` | List profile assignments |
| `PUT` | `/profiles/{profile_id}/assignments/{device_id}/status` | Update assignment status |

### `GET /profiles`

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
      "name": "Base Security Profile",
      "description": "Standard security configuration",
      "version": 1,
      "policy": {
        "cameraAccess": 2,
        "locationMode": 1,
        "bluetoothDisabled": false
      },
      "scope": {
        "targets": [
          {"scopeType": "ALL_DEVICES", "targetId": null}
        ],
        "exclusions": []
      },
      "createdBy": 1,
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 100
}
```

### `GET /profiles/{profile_id}`

**Path parameters:** `profile_id` (int)

**Response `200`:** Single `ProfileResponse` object.

**Response `404`:** `{"detail": "Profile not found"}`

### `POST /profiles`

**Request body:**

```json
{
  "name": "Base Security Profile",
  "description": "Standard security configuration",
  "policy": {
    "cameraAccess": 2,
    "locationMode": 1
  },
  "scope": {
    "targets": [
      {"scopeType": "ALL_DEVICES", "targetId": null}
    ],
    "exclusions": []
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Unique profile name |
| `description` | string | No | Optional description |
| `policy` | object | Yes | Policy payload (Android Management API model) |
| `scope` | object | Yes | Scope with `targets` and `exclusions` |

Triggers `ProfileAssignmentReconciler` recalculation if scope has targets.

**Response `201`:** Created `ProfileResponse` object.

### `PUT /profiles/{profile_id}`

**Path parameters:** `profile_id` (int)

**Request body** (partial):

```json
{
  "policy": {
    "cameraAccess": 3,
    "bluetoothDisabled": true
  },
  "scope": {
    "targets": [
      {"scopeType": "SMART_GROUP", "targetId": 1}
    ],
    "exclusions": []
  }
}
```

Triggers reconciler recalculation when `scope` or `policy` changes.

**Response `200`:** Updated `ProfileResponse` object.

**Response `404`:** `{"detail": "Profile not found"}`

### `DELETE /profiles/{profile_id}`

**Path parameters:** `profile_id` (int)

Fails if the profile has scope targets defined — scope must be cleared first.

**Response `204`:** No content.

**Response `404`:** `{"detail": "Profile not found"}`

### `GET /profiles/{profile_id}/assignments`

**Path parameters:** `profile_id` (int)

**Response `200`:**

```json
[
  {
    "id": 1,
    "profileId": 1,
    "deviceId": 1,
    "status": "PENDING",
    "desiredState": "PRESENT",
    "profileVersion": 1,
    "assignedAt": "2025-01-01T00:00:00Z",
    "appliedAt": null,
    "revokedAt": null,
    "attemptCount": 0,
    "lastAttemptAt": null,
    "lastError": null,
    "messageId": null,
    "updatedAt": null
  }
]
```

### `PUT /profiles/{profile_id}/assignments/{device_id}/status`

**Path parameters:** `profile_id` (int), `device_id` (int)

**Request body:**

```json
{
  "status": "APPLIED"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `status` | string | Yes | One of `PENDING`, `SENT`, `APPLIED`, `FAILED`, `REVOKE_PENDING`, `REVOKED` |

**Response `200`:** Updated `AssignmentResponse` object.

**Response `404`:** `{"detail": "Assignment not found"}`

## Smart Groups

| Method | Path | Description |
|---|---|---|
| `GET` | `/smart-groups` | List all smart groups (paginated) |
| `GET` | `/smart-groups/{group_id}` | Get group by ID |
| `POST` | `/smart-groups` | Create a smart group |
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
      "criteria": [
        {"field": "connectionStatus", "operator": "is", "type": "STRING", "value": "Connected"}
      ],
      "createdBy": 1,
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 100
}
```

### `GET /smart-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Response `200`:** Single `SmartGroupResponse` object.

**Response `404`:** `{"detail": "Smart group not found"}`

### `POST /smart-groups`

**Request body:**

```json
{
  "name": "Engineering",
  "description": "Engineering department",
  "criteria": [
    {"field": "connectionStatus", "operator": "is", "type": "STRING", "value": "Connected"}
  ]
}
```

`name` and `criteria` required, `description` optional. `criteria` must be a non-empty list of `Criteria` objects.

**Response `201`:** Created `SmartGroupResponse` object.

### `PUT /smart-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Request body** (at least one field):

```json
{
  "name": "Engineering Team",
  "criteria": [
    {"field": "osVersion", "operator": "is", "type": "STRING", "value": "15.0"}
  ]
}
```

Triggers `ProfileAssignmentReconciler` recalculation on criteria change.

**Response `200`:** Updated `SmartGroupResponse` object.

**Response `404`:** `{"detail": "Smart group not found"}`

### `DELETE /smart-groups/{group_id}`

**Path parameters:** `group_id` (int)

Triggers reconciler cleanup (removes all scope references to this group).

**Response `204`:** No content.

**Response `404`:** `{"detail": "Smart group not found"}`

## Static Groups

| Method | Path | Description |
|---|---|---|
| `GET` | `/static-groups` | List all static groups (paginated) |
| `GET` | `/static-groups/{group_id}` | Get group by ID |
| `POST` | `/static-groups` | Create a static group |
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
      "createdBy": 1,
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z",
      "devices": []
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 100
}
```

### `GET /static-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Response `200`:** Single `StaticGroupResponse` object.

**Response `404`:** `{"detail": "Static group not found"}`

### `POST /static-groups`

**Request body:**

```json
{
  "name": "Marketing",
  "description": "Marketing department",
  "deviceSerialNumbers": ["SN001", "SN002"]
}
```

`name` required, `description` and `deviceSerialNumbers` optional.

**Response `201`:** Created `StaticGroupResponse` object.

### `PUT /static-groups/{group_id}`

**Path parameters:** `group_id` (int)

**Request body** (at least one field):

```json
{
  "name": "Marketing Team",
  "deviceSerialNumbers": ["SN001", "SN003"]
}
```

Triggers reconciler when device membership changes.

**Response `200`:** Updated `StaticGroupResponse` object.

**Response `404`:** `{"detail": "Static group not found"}`

### `DELETE /static-groups/{group_id}`

**Path parameters:** `group_id` (int)

Triggers reconciler cleanup.

**Response `204`:** No content.

**Response `404`:** `{"detail": "Static group not found"}`

## Mobile Apps

| Method | Path | Description |
|---|---|---|
| `GET` | `/mobile-apps` | List all mobile apps (paginated) |
| `GET` | `/mobile-apps/{mobile_app_id}` | Get app by ID |
| `POST` | `/mobile-apps` | Create a mobile app |
| `PUT` | `/mobile-apps/{mobile_app_id}` | Update a mobile app |
| `DELETE` | `/mobile-apps/{mobile_app_id}` | Delete a mobile app |

### `GET /mobile-apps`

**Query parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `skip` | int | `0` | Number of items to skip |
| `limit` | int | `100` | Max items to return |

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Zoom",
      "enabled": true,
      "version": "5.0",
      "packageName": "us.zoom.videomeetings",
      "scope": {
        "targets": [],
        "exclusions": []
      },
      "createdBy": 1,
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 100
}
```

### `POST /mobile-apps`

**Request body:**

```json
{
  "name": "Zoom",
  "enabled": true,
  "version": "5.0",
  "packageName": "us.zoom.videomeetings",
  "scope": {
    "targets": [],
    "exclusions": []
  }
}
```

## Extension Attributes

| Method | Path | Description |
|---|---|---|
| `GET` | `/extension-attributes` | List all extension attributes (paginated) |
| `GET` | `/extension-attributes/{attribute_id}` | Get attribute by ID |
| `POST` | `/extension-attributes` | Create an extension attribute |
| `PUT` | `/extension-attributes/{attribute_id}` | Update an extension attribute |
| `DELETE` | `/extension-attributes/{attribute_id}` | Delete an extension attribute |

### `GET /extension-attributes`

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Department",
      "description": "Employee department",
      "dataType": "string",
      "inputType": "Pop-up menu",
      "popupChoices": ["Engineering", "Marketing", "Sales"],
      "createdBy": 1,
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": null
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 100
}
```

### `POST /extension-attributes`

**Request body:**

```json
{
  "name": "Department",
  "description": "Employee department",
  "dataType": "string",
  "inputType": "Pop-up menu",
  "popupChoices": ["Engineering", "Marketing", "Sales"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Attribute name |
| `description` | string | No | Optional description |
| `dataType` | string | Yes | `string`, `integer`, or `date` |
| `inputType` | string | Yes | `Text field` or `Pop-up menu` |
| `popupChoices` | list[string] | No | Required if `inputType` is `Pop-up menu` |

## Inventory Search

| Method | Path | Description |
|---|---|---|
| `GET` | `/inventory-search` | List saved searches (paginated) |
| `GET` | `/inventory-search/{search_id}` | Get search by ID |
| `POST` | `/inventory-search` | Create a saved search |
| `PUT` | `/inventory-search/{search_id}` | Update a saved search |
| `DELETE` | `/inventory-search/{search_id}` | Delete a saved search |
| `POST` | `/inventory-search/execute` | Execute a search with ad-hoc criteria |

### `GET /inventory-search`

**Response `200`:**

```json
{
  "items": [
    {
      "id": 1,
      "name": "Online Macs",
      "description": "Macs currently connected",
      "criteria": [
        {"field": "connectionStatus", "operator": "is", "type": "STRING", "value": "Connected"}
      ],
      "createdBy": 1,
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 100
}
```

### `POST /inventory-search/execute`

Executes a search with ad-hoc criteria against the device inventory. Does not create or modify any saved search.

**Request body:**

```json
{
  "criteria": [
    {"field": "connectionStatus", "operator": "is", "type": "STRING", "value": "Connected"}
  ]
}
```

`criteria` is a non-empty array of `Criteria` objects.

**Response `200`:** Array of `DeviceResponse` objects.

## Users

| Method | Path | Description |
|---|---|---|
| `GET` | `/users` | List all users (paginated) |
| `GET` | `/users/{user_id}` | Get user by ID |
| `GET` | `/users/by-email/{email}` | Get user by email |
| `POST` | `/users` | Create a user |
| `PUT` | `/users/{user_id}` | Update a user |
| `DELETE` | `/users/{user_id}` | Delete a user |

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
      "email": "alice@example.com",
      "name": "Alice",
      "permissions": ["admin"],
      "createdAt": "2025-01-01T00:00:00Z",
      "updatedAt": "2025-01-01T00:00:00Z",
      "lastLoginAt": null
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

### `POST /users`

**Request body:**

```json
{
  "email": "bob@example.com",
  "name": "Bob",
  "permissions": ["viewer"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `email` | string | Yes | User email |
| `name` | string | Yes | Display name |
| `permissions` | list | No | One or more of `admin`, `editor`, `viewer` (default: `["viewer"]`) |

**Response `201`:** Created `UserResponse` object.

### `PUT /users/{user_id}`

**Path parameters:** `user_id` (int)

**Request body** (at least one field):

```json
{
  "name": "Bob Smith",
  "permissions": ["editor"]
}
```

**Response `200`:** Updated `UserResponse` object.

**Response `404`:** `{"detail": "User not found"}`

### `DELETE /users/{user_id}`

**Path parameters:** `user_id` (int)

**Response `204`:** No content.

**Response `404`:** `{"detail": "User not found"}`

## Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Database and RabbitMQ health check |

### `GET /health`

**Response `200`:**

```json
{
  "status": "ok",
  "database": "ok",
  "rabbitmq": "ok"
}
```

**Response `503`:**

```json
{
  "status": "error",
  "database": "error",
  "rabbitmq": "disconnected"
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
- `limit` — max records returned (capped at 1000)
- `total` — total matching records in the database

## Common Responses

| Status | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `204` | Deleted (no content) |
| `400` | Bad request — missing or invalid parameters |
| `404` | Resource not found |
| `503` | Service unavailable (health check) |
