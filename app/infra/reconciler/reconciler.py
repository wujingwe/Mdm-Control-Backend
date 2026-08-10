import logging
from collections.abc import Awaitable, Callable, Mapping
from functools import partial
from typing import Protocol, TypeVar

from app.domains.devices.repositories import DeviceRepository
from app.domains.mobile_apps.models import MobileApp, MobileAppAssignment
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.mobile_apps.schemas import MobileAppAssignmentUpsert
from app.domains.profiles.enums import AssignmentDesiredState, AssignmentStatus
from app.domains.profiles.models import Profile, ProfileAssignment
from app.domains.profiles.repositories import ProfileRepository
from app.domains.profiles.schemas.profile import AssignmentUpsert
from app.domains.shared.scope import Scope, ScopeExclusion, ScopeTarget, ScopeType
from app.domains.smart_groups.repositories import SmartGroupRepository
from app.infra.messaging.producer import RabbitMQProducer

logger = logging.getLogger(__name__)


class _AssignmentUpsert(Protocol):
    device_id: int


class _Assignment(Protocol):
    id: int


T = TypeVar("T", bound=_AssignmentUpsert)

ScopeKey = tuple[ScopeType, int | None]


class AssignmentReconciler:
    """Reconcile profile and mobile app scope intent with device assignment revisions."""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        mobile_app_repo: MobileAppRepository,
        device_repo: DeviceRepository,
        smart_group_repo: SmartGroupRepository,
        producer: RabbitMQProducer,
    ) -> None:
        self.profile_repo = profile_repo
        self.mobile_app_repo = mobile_app_repo
        self.device_repo = device_repo
        self.smart_group_repo = smart_group_repo
        self.producer = producer

    # ── Profile methods ──────────────────────────────────────────────────

    @staticmethod
    def _compute_assignments(
        scope: Scope,
        resolved_device_ids: dict[ScopeKey, set[int]],
        build_upsert: Callable[[int], T],
    ) -> list[T]:
        wanted: dict[ScopeKey, set[int]] = {}
        for target in scope.targets:
            source_key = (target.scope_type, target.target_id)
            wanted.setdefault(source_key, set()).update(resolved_device_ids.get(source_key, set()))

        assignments: list[T] = []
        seen: set[int] = set()

        for device_ids in wanted.values():
            for device_id in device_ids:
                if device_id in seen:
                    continue
                seen.add(device_id)
                assignments.append(build_upsert(device_id))

        if scope.exclusions:
            excluded_ids: set[int] = set()
            for exclusion in scope.exclusions:
                key = (exclusion.scope_type, exclusion.exclude_id)
                excluded_ids.update(resolved_device_ids.get(key, set()))
            assignments = [a for a in assignments if a.device_id not in excluded_ids]

        return assignments

    @staticmethod
    def compute_profile(
        profile_id: int,
        profile_version: int,
        scope: Scope,
        resolved_device_ids: dict[ScopeKey, set[int]],
    ) -> list[AssignmentUpsert]:
        return AssignmentReconciler._compute_assignments(
            scope,
            resolved_device_ids,
            build_upsert=lambda device_id: AssignmentUpsert(
                profile_id=profile_id,
                device_id=device_id,
                status=AssignmentStatus.PENDING,
                profile_version=profile_version,
            ),
        )

    async def recalculate_profile(self, profile_id: int, *, force_push: bool = False) -> None:
        profile = await self.profile_repo.get_by_id_for_update(profile_id)
        if not profile:
            return

        current_ids = await self.profile_repo.get_current_desired_device_ids(profile_id)
        resolved = await self._resolve_scope(profile.scope) if profile.scope.targets else {}
        assignments = self.compute_profile(
            profile_id=profile_id,
            profile_version=profile.version,
            scope=profile.scope,
            resolved_device_ids=resolved,
        )
        desired_ids = {a.device_id for a in assignments}

        new_ids = desired_ids - current_ids
        revoked_ids = current_ids - desired_ids

        if not new_ids and not revoked_ids and not force_push:
            return

        version = await self.profile_repo.write_revision(profile, desired_ids, revoked_device_ids=revoked_ids)

        push_ids = desired_ids if force_push else new_ids
        current_assignments = await self.profile_repo.get_current_assignments(profile_id)
        present_assignments = {
            assignment.device_id: assignment
            for assignment in current_assignments
            if assignment.profile_version == version and assignment.desired_state == AssignmentDesiredState.PRESENT
        }
        absent_assignments = {
            assignment.device_id: assignment
            for assignment in current_assignments
            if assignment.profile_version == version and assignment.desired_state == AssignmentDesiredState.ABSENT
        }
        if push_ids:
            await self._send_push_messages(
                profile,
                push_ids,
                present_assignments,
                version,
            )
        if revoked_ids:
            await self._send_revoke_messages(
                profile,
                revoked_ids,
                absent_assignments,
                version,
            )

    # ── Mobile App methods ──────────────────────────────────────────────

    @staticmethod
    def compute_mobile_app(
        mobile_app_id: int,
        app_version: int,
        scope: Scope,
        resolved_device_ids: dict[ScopeKey, set[int]],
    ) -> list[MobileAppAssignmentUpsert]:
        return AssignmentReconciler._compute_assignments(
            scope,
            resolved_device_ids,
            build_upsert=lambda device_id: MobileAppAssignmentUpsert(
                mobile_app_id=mobile_app_id,
                device_id=device_id,
                status=AssignmentStatus.PENDING,
                version=app_version,
            ),
        )

    async def recalculate_mobile_app(self, mobile_app_id: int, *, force_push: bool = False) -> None:
        app = await self.mobile_app_repo.get_by_id_for_update(mobile_app_id)
        if not app:
            return

        current_ids = await self.mobile_app_repo.get_current_desired_device_ids(mobile_app_id)
        resolved = await self._resolve_scope(app.scope) if app.scope.targets else {}
        assignments = self.compute_mobile_app(
            mobile_app_id=mobile_app_id,
            app_version=app.version,
            scope=app.scope,
            resolved_device_ids=resolved,
        )
        desired_ids = {a.device_id for a in assignments}

        new_ids = desired_ids - current_ids
        revoked_ids = current_ids - desired_ids

        if not new_ids and not revoked_ids and not force_push:
            return

        version = await self.mobile_app_repo.write_revision(app, desired_ids, revoked_device_ids=revoked_ids)

        push_ids = desired_ids if force_push else new_ids
        current_assignments = await self.mobile_app_repo.get_current_assignments(mobile_app_id)
        present_assignments = {
            assignment.device_id: assignment
            for assignment in current_assignments
            if assignment.version == version and assignment.desired_state == AssignmentDesiredState.PRESENT
        }
        absent_assignments = {
            assignment.device_id: assignment
            for assignment in current_assignments
            if assignment.version == version and assignment.desired_state == AssignmentDesiredState.ABSENT
        }
        if push_ids:
            await self._send_mobile_app_push_messages(
                app,
                push_ids,
                present_assignments,
                version,
            )
        if revoked_ids:
            await self._send_mobile_app_revoke_messages(
                app,
                revoked_ids,
                absent_assignments,
                version,
            )

    # ── Shared helpers ──────────────────────────────────────────────────

    async def _resolve_scope(self, scope: Scope) -> dict[ScopeKey, set[int]]:
        result: dict[ScopeKey, set[int]] = {}

        for target in scope.targets:
            device_ids = await self._resolve_target_ids(target)
            if device_ids:
                key = (target.scope_type, target.target_id)
                result.setdefault(key, set()).update(device_ids)

        for exclusion in scope.exclusions:
            device_ids = await self._resolve_exclusion_ids(exclusion)
            if device_ids:
                key = (exclusion.scope_type, exclusion.exclude_id)
                result.setdefault(key, set()).update(device_ids)

        return result

    async def _resolve_target_ids(self, target: ScopeTarget) -> set[int]:
        if target.scope_type == ScopeType.ALL_DEVICES:
            return await self.device_repo.list_enrolled_ids()

        if target.scope_type == ScopeType.SMART_GROUP and target.target_id:
            return await self.smart_group_repo.resolve_device_ids(target.target_id)

        if target.scope_type == ScopeType.STATIC_GROUP and target.target_id:
            return await self.device_repo.resolve_device_ids(target.target_id)

        if target.scope_type == ScopeType.DEVICE and target.target_id:
            device_id = await self.device_repo.get_enrolled_id(target.target_id)
            return {device_id} if device_id is not None else set()

        return set()

    async def _resolve_exclusion_ids(self, exclusion: ScopeExclusion) -> set[int]:
        if exclusion.scope_type == ScopeType.DEVICE and exclusion.exclude_id:
            return {exclusion.exclude_id}

        if exclusion.scope_type == ScopeType.SMART_GROUP and exclusion.exclude_id:
            return await self.smart_group_repo.resolve_device_ids(exclusion.exclude_id)

        if exclusion.scope_type == ScopeType.STATIC_GROUP and exclusion.exclude_id:
            return await self.device_repo.resolve_device_ids(exclusion.exclude_id)

        return set()

    # ── Message helpers ─────────────────────────────────────────────────

    async def _dispatch_messages(
        self,
        device_ids: set[int],
        assignments: Mapping[int, _Assignment],
        *,
        publish: Callable[..., Awaitable[str]],
        mark_sent: Callable[[int, str], Awaitable[None]],
        mark_failed: Callable[[int, str], Awaitable[None]],
        action: str,
        entity: str,
        entity_id: int,
    ) -> None:
        serial_map = await self.device_repo.get_serial_map(device_ids)
        for device_id in sorted(device_ids):
            serial = serial_map.get(device_id)
            if not serial:
                continue
            assignment = assignments.get(device_id)
            if assignment is None:
                logger.warning(
                    "Skipping %s for %s %s to device %s: no assignment row",
                    action,
                    entity,
                    entity_id,
                    device_id,
                )
                continue
            try:
                message_id = await publish(
                    serial_number=serial,
                    assignment_id=assignment.id,
                )
                await mark_sent(assignment.id, message_id)
            except Exception as exc:
                await mark_failed(assignment.id, str(exc))
                logger.exception(
                    "Failed to send %s for %s %s to device %s",
                    action,
                    entity,
                    entity_id,
                    device_id,
                )

    async def _send_push_messages(
        self,
        profile: Profile,
        device_ids: set[int],
        assignments: dict[int, ProfileAssignment],
        version: int,
    ) -> None:
        await self._dispatch_messages(
            device_ids,
            assignments,
            publish=partial(
                self.producer.publish_profile_push,
                profile_id=profile.id,
                profile_config=profile.policy,
                profile_version=version,
            ),
            mark_sent=self.profile_repo.mark_assignment_sent,
            mark_failed=self.profile_repo.mark_assignment_failed,
            action="push",
            entity="profile",
            entity_id=profile.id,
        )

    async def _send_revoke_messages(
        self,
        profile: Profile,
        device_ids: set[int],
        assignments: dict[int, ProfileAssignment],
        version: int,
    ) -> None:
        await self._dispatch_messages(
            device_ids,
            assignments,
            publish=partial(
                self.producer.publish_profile_revoke,
                profile_id=profile.id,
                profile_version=version,
            ),
            mark_sent=self.profile_repo.mark_assignment_sent,
            mark_failed=self.profile_repo.mark_assignment_failed,
            action="revoke",
            entity="profile",
            entity_id=profile.id,
        )

    async def _send_mobile_app_push_messages(
        self,
        app: MobileApp,
        device_ids: set[int],
        assignments: dict[int, MobileAppAssignment],
        version: int,
    ) -> None:
        await self._dispatch_messages(
            device_ids,
            assignments,
            publish=partial(
                self.producer.publish_mobile_app_push,
                mobile_app_id=app.id,
                package_name=app.package_name,
                package_version=app.package_version,
                app_version=version,
            ),
            mark_sent=self.mobile_app_repo.mark_assignment_sent,
            mark_failed=self.mobile_app_repo.mark_assignment_failed,
            action="push",
            entity="mobile app",
            entity_id=app.id,
        )

    async def _send_mobile_app_revoke_messages(
        self,
        app: MobileApp,
        device_ids: set[int],
        assignments: dict[int, MobileAppAssignment],
        version: int,
    ) -> None:
        await self._dispatch_messages(
            device_ids,
            assignments,
            publish=partial(
                self.producer.publish_mobile_app_revoke,
                mobile_app_id=app.id,
                package_name=app.package_name,
                app_version=version,
            ),
            mark_sent=self.mobile_app_repo.mark_assignment_sent,
            mark_failed=self.mobile_app_repo.mark_assignment_failed,
            action="revoke",
            entity="mobile app",
            entity_id=app.id,
        )
