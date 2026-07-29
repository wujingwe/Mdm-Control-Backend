# Profiles with non-empty scopes cannot be deleted

A Profile cannot be deleted while it has scope targets defined. The user must first clear the scope, which triggers reconciliation and naturally revokes the profile from all devices via ABSENT assignment rows. Only when the scope is empty — meaning no devices are desired — can the Profile be deleted. Historical assignment rows cascade-delete with the Profile.

This eliminates the need for special-case revoke-on-delete logic and ensures no device retains a policy whose backend record no longer exists. The trade-off is a stricter deletion workflow: users cannot delete a profile in one step if it is actively scoped.
