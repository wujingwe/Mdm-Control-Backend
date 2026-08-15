import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Protocol, Sequence, TypeVar

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
    device_id: int
    desired_state: AssignmentDesiredState
    attempt_count: int
    last_attempt_at: datetime | None


class _MessagePublisher(Protocol):
    async def __call__(
        self,
        *,
        serial_number: str,
        assignment_id: int,
    ) -> str: ...


@dataclass(frozen=True)
class _DispatchSpec:
    publish: _MessagePublisher
    mark_sent: Callable[[dict[int, str]], Awaitable[None]]
    mark_failed: Callable[[dict[int, str]], Awaitable[None]]
    action: str
    entity: str
    entity_id: int


T = TypeVar("T", bound=_AssignmentUpsert)

ScopeKey = tuple[ScopeType, int | None]

DEFAULT_BACKOFF_SECONDS: tuple[int, ...] = (60, 300, 900, 1800, 3600)


@dataclass
class SweepResult:
    """Counts from a stale-assignment sweep."""

    profile_push_sent: int = 0
    profile_push_failed: int = 0
    profile_revoke_sent: int = 0
    profile_revoke_failed: int = 0
    mobile_app_push_sent: int = 0
    mobile_app_push_failed: int = 0
    mobile_app_revoke_sent: int = 0
    mobile_app_revoke_failed: int = 0
    gave_up: int = 0


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
        current_version_assignments = [a for a in current_assignments if a.profile_version == version]
        present_assignment_ids, absent_assignment_ids = self._split_present_absent(current_version_assignments)
        if push_ids:
            await self._send_push_messages(profile, push_ids, present_assignment_ids, version)
        if revoked_ids:
            await self._send_revoke_messages(profile, revoked_ids, absent_assignment_ids, version)

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
        current_version_assignments = [a for a in current_assignments if a.version == version]
        present_assignment_ids, absent_assignment_ids = self._split_present_absent(current_version_assignments)
        if push_ids:
            await self._send_mobile_app_push_messages(app, push_ids, present_assignment_ids, version)
        if revoked_ids:
            await self._send_mobile_app_revoke_messages(app, revoked_ids, absent_assignment_ids, version)

    # ── Shared helpers ──────────────────────────────────────────────────

    @staticmethod
    def _split_present_absent(
        assignments: Sequence[_Assignment],
    ) -> tuple[dict[int, int], dict[int, int]]:
        """Split current-revision assignment rows into PRESENT/ABSENT id maps.

        Returns ``(present, absent)`` maps of ``device_id -> assignment_id``.
        """
        present: dict[int, int] = {}
        absent: dict[int, int] = {}
        for assignment in assignments:
            target = present if assignment.desired_state == AssignmentDesiredState.PRESENT else absent
            target[assignment.device_id] = assignment.id
        return present, absent

    async def _resolve_scope(self, scope: Scope) -> dict[ScopeKey, set[int]]:
        result: dict[ScopeKey, set[int]] = {}
        target_cache: dict[ScopeKey, set[int]] = {}
        exclusion_cache: dict[ScopeKey, set[int]] = {}

        for target in scope.targets:
            key = (target.scope_type, target.target_id)
            if key not in target_cache:
                target_cache[key] = await self._resolve_target_ids(target)
            device_ids = target_cache[key]
            if device_ids:
                result.setdefault(key, set()).update(device_ids)

        for exclusion in scope.exclusions:
            key = (exclusion.scope_type, exclusion.exclude_id)
            if key not in exclusion_cache:
                exclusion_cache[key] = await self._resolve_exclusion_ids(exclusion)
            device_ids = exclusion_cache[key]
            if device_ids:
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

    @staticmethod
    def _is_due(
        assignment: _Assignment,
        now: datetime,
        backoff_seconds: tuple[int, ...] = DEFAULT_BACKOFF_SECONDS,
    ) -> bool:
        """Whether a current-revision assignment is ready to be re-sent.

        Never-attempted rows are immediately due. Otherwise the elapsed time
        since ``last_attempt_at`` must exceed the backoff for the attempt
        count, and there must be attempts left.
        """
        if assignment.attempt_count >= len(backoff_seconds):
            return False
        if assignment.last_attempt_at is None:
            return True
        last_attempt_at = assignment.last_attempt_at
        if last_attempt_at.tzinfo is None:
            last_attempt_at = last_attempt_at.replace(tzinfo=timezone.utc)
        return last_attempt_at < now - timedelta(seconds=backoff_seconds[assignment.attempt_count])

    async def sweep_stale_assignments(
        self,
        *,
        limit: int = 500,
        backoff_seconds: tuple[int, ...] = DEFAULT_BACKOFF_SECONDS,
    ) -> SweepResult:
        """Re-send assignments that were never acknowledged by devices.

        Scans current-revision profile and mobile app assignments, and
        re-publishes push/revoke messages for rows that are not in a
        terminal state (APPLIED/REVOKED), have retries left per the backoff
        schedule, and are due. Rows that are out of retries or not yet due
        are counted as ``gave_up`` and left untouched.
        """
        now = datetime.now(timezone.utc)
        result = SweepResult()
        min_elapsed = timedelta(seconds=backoff_seconds[0]) if backoff_seconds else timedelta(seconds=0)

        profile_groups: dict[int, list[ProfileAssignment]] = {}
        for profile_assignment in await self.profile_repo.list_due_assignments(
            min_retry_elapsed=min_elapsed,
            limit=limit,
        ):
            if self._is_due(profile_assignment, now, backoff_seconds):
                profile_groups.setdefault(profile_assignment.profile_id, []).append(profile_assignment)
            else:
                result.gave_up += 1

        app_groups: dict[int, list[MobileAppAssignment]] = {}
        for app_assignment in await self.mobile_app_repo.list_due_assignments(
            min_retry_elapsed=min_elapsed,
            limit=limit,
        ):
            if self._is_due(app_assignment, now, backoff_seconds):
                app_groups.setdefault(app_assignment.mobile_app_id, []).append(app_assignment)
            else:
                result.gave_up += 1

        for profile_id, profile_candidates in profile_groups.items():
            profile = await self.profile_repo.get_by_id(profile_id)
            if not profile:
                continue
            current = {a.device_id: a for a in await self.profile_repo.get_current_assignments(profile_id)}
            device_ids = {
                a.device_id
                for a in profile_candidates
                if a.device_id in current
                and current[a.device_id].status not in (AssignmentStatus.APPLIED, AssignmentStatus.REVOKED)
            }
            if not device_ids:
                continue
            present, absent = self._split_present_absent([current[d] for d in device_ids])
            if present:
                sent, failed = await self._send_push_messages(profile, set(present), present, profile.version)
                result.profile_push_sent += sent
                result.profile_push_failed += failed
            if absent:
                sent, failed = await self._send_revoke_messages(profile, set(absent), absent, profile.version)
                result.profile_revoke_sent += sent
                result.profile_revoke_failed += failed

        for app_id, app_candidates in app_groups.items():
            app = await self.mobile_app_repo.get_by_id(app_id)
            if not app:
                continue
            current_apps = {a.device_id: a for a in await self.mobile_app_repo.get_current_assignments(app_id)}
            device_ids = {
                a.device_id
                for a in app_candidates
                if a.device_id in current_apps
                and current_apps[a.device_id].status not in (AssignmentStatus.APPLIED, AssignmentStatus.REVOKED)
            }
            if not device_ids:
                continue
            present, absent = self._split_present_absent([current_apps[d] for d in device_ids])
            if present:
                sent, failed = await self._send_mobile_app_push_messages(app, set(present), present, app.version)
                result.mobile_app_push_sent += sent
                result.mobile_app_push_failed += failed
            if absent:
                sent, failed = await self._send_mobile_app_revoke_messages(app, set(absent), absent, app.version)
                result.mobile_app_revoke_sent += sent
                result.mobile_app_revoke_failed += failed

        return result

    async def _dispatch_messages(
        self,
        device_ids: set[int],
        assignments: dict[int, int],
        *,
        spec: _DispatchSpec,
    ) -> tuple[int, int]:
        """Publish to each device and mark rows sent/failed.

        Returns ``(sent_count, failed_count)``.
        """
        serial_map = await self.device_repo.get_serial_map(device_ids)
        sent: dict[int, str] = {}
        failed: dict[int, str] = {}
        for device_id in sorted(device_ids):
            serial = serial_map.get(device_id)
            if not serial:
                continue
            assignment_id = assignments.get(device_id)
            if assignment_id is None:
                logger.warning(
                    "Skipping %s for %s %s to device %s: no assignment row",
                    spec.action,
                    spec.entity,
                    spec.entity_id,
                    device_id,
                )
                continue
            try:
                message_id = await spec.publish(
                    serial_number=serial,
                    assignment_id=assignment_id,
                )
                sent[assignment_id] = message_id
            except Exception as exc:
                failed[assignment_id] = str(exc)
                logger.exception(
                    "Failed to send %s for %s %s to device %s",
                    spec.action,
                    spec.entity,
                    spec.entity_id,
                    device_id,
                )
        if sent:
            await spec.mark_sent(sent)
        if failed:
            await spec.mark_failed(failed)
        return len(sent), len(failed)

    async def _send_push_messages(
        self, profile: Profile, device_ids: set[int], assignments: dict[int, int], version: int
    ) -> tuple[int, int]:
        return await self._dispatch_messages(
            device_ids,
            assignments,
            spec=_DispatchSpec(
                publish=partial(
                    self.producer.publish_profile_push,
                    profile_id=profile.id,
                    profile_config=profile.policy,
                    profile_version=version,
                ),
                mark_sent=self.profile_repo.mark_assignments_sent,
                mark_failed=self.profile_repo.mark_assignments_failed,
                action="push",
                entity="profile",
                entity_id=profile.id,
            ),
        )

    async def _send_revoke_messages(
        self, profile: Profile, device_ids: set[int], assignments: dict[int, int], version: int
    ) -> tuple[int, int]:
        return await self._dispatch_messages(
            device_ids,
            assignments,
            spec=_DispatchSpec(
                publish=partial(
                    self.producer.publish_profile_revoke,
                    profile_id=profile.id,
                    profile_version=version,
                ),
                mark_sent=self.profile_repo.mark_assignments_sent,
                mark_failed=self.profile_repo.mark_assignments_failed,
                action="revoke",
                entity="profile",
                entity_id=profile.id,
            ),
        )

    async def _send_mobile_app_push_messages(
        self, app: MobileApp, device_ids: set[int], assignments: dict[int, int], version: int
    ) -> tuple[int, int]:
        return await self._dispatch_messages(
            device_ids,
            assignments,
            spec=_DispatchSpec(
                publish=partial(
                    self.producer.publish_mobile_app_push,
                    mobile_app_id=app.id,
                    package_name=app.package_name,
                    package_version=app.package_version,
                    app_version=version,
                ),
                mark_sent=self.mobile_app_repo.mark_assignments_sent,
                mark_failed=self.mobile_app_repo.mark_assignments_failed,
                action="push",
                entity="mobile app",
                entity_id=app.id,
            ),
        )

    async def _send_mobile_app_revoke_messages(
        self, app: MobileApp, device_ids: set[int], assignments: dict[int, int], version: int
    ) -> tuple[int, int]:
        return await self._dispatch_messages(
            device_ids,
            assignments,
            spec=_DispatchSpec(
                publish=partial(
                    self.producer.publish_mobile_app_revoke,
                    mobile_app_id=app.id,
                    package_name=app.package_name,
                    app_version=version,
                ),
                mark_sent=self.mobile_app_repo.mark_assignments_sent,
                mark_failed=self.mobile_app_repo.mark_assignments_failed,
                action="revoke",
                entity="mobile app",
                entity_id=app.id,
            ),
        )
