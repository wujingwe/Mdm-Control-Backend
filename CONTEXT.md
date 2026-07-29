# MDM Control Backend

Backend service for a Mobile Device Management (MDM) control plane. Manages device enrollment, configuration profiles, group scoping, and command dispatch.

## Language

**Profile**:
A versioned, scoppable configuration entity that manages a fleet of devices. Owns lifecycle, versioning, and scope.
_Avoid_: Policy (when referring to the entity as a whole)

**Policy**:
The configuration payload embedded inside a Profile. Modeled after the Android Management API — camera access, wifi, app install rules, security overrides, etc. Sent to devices as-is.
_Avoid_: Configuration, settings

**SmartGroup**:
A device group whose membership is determined dynamically by criteria evaluated against device attributes at query time. Its type is immutable at creation — a group born smart stays smart.
_Avoid_: Dynamic group, filter group

**StaticGroup**:
A device group whose membership is assigned explicitly by adding or removing devices. Its type is immutable at creation — a group born static stays static.
_Avoid_: Manual group, fixed group

**Scope**:
The set of inclusion targets and exclusion targets attached to a Profile. Resolved to a flat device set at reconciliation time via set arithmetic: union all targets, then subtract exclusions. Each target references an entity by type (ALL_DEVICES, SMART_GROUP, STATIC_GROUP, or DEVICE) and ID.

**ProfileAssignment**:
A versioned, append-only record linking a Profile to a specific Device at a specific Profile version. Each recalculation produces a new revision containing PRESENT rows (device should receive the profile) and ABSENT rows (device should have the profile removed). The current state of a device is determined by the highest-numbered revision for that (profile, device) pair.
_Avoid_: Profile mapping, policy assignment

**MobileApp**:
A Profile-like entity for mobile application distribution. Has its own scope and will eventually support assignments, reconciliation, and versioning comparable to Profile, but that functionality has not yet been built.
_Avoid_: App, application

**Device**:
A managed mobile device identified by serial number. Only devices with enrollment status Enrolled are eligible for Profile assignment. Assignments are preserved across unenrollment — desired configuration persists and is reapplied on re-enrollment.
_Avoid_: Endpoint, handset
