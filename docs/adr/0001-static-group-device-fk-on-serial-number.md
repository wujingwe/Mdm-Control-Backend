# StaticGroupDevice FKs on serial_number, not devices.id

`static_group_devices` uses `device_serial_number` as its foreign key to `devices` instead of `devices.id` like every other junction table. This is intentional: `serial_number` is the shared identity contract between the backend and the mobile frontend. The frontend knows devices by serial number — it never sees `devices.id`, which is an internal surrogate key. Using serial_number as the FK ensures group membership operations can be communicated directly with the frontend without an ID lookup step.

The trade-off is inconsistency with other junction tables (`profile_assignments`, `device_commands`) that FK on `devices.id`, and the loss of a database-level FK constraint on a numeric primary key. This was accepted because the frontend integration requirement outweighs internal consistency.
