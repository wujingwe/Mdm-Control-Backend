import logging

from sqlalchemy import select

from app.common.enums import AssignmentDesiredState, DeviceStatus
from app.common.schemas import Exclusion, Scope, ScopeType, Target
from app.criteria import build_device_query
from app.criteria.schemas import Criteria
from app.devices.models import Device
from app.messaging.producer import RabbitMQProducer
from app.profiles.calculator import AssignmentCalculator
from app.profiles.models import Profile, ProfileAssignment
from app.profiles.repositories import ProfileRepository
from app.smart_groups.models import SmartGroup
from app.static_groups.models import StaticGroupDevice

logger = logging.getLogger(__name__)


class ProfileAssignmentReconciler:
    """Reconcile profile scope intent with immutable device assignment revisions.

    A recalculation compares the devices currently desired by the latest
    assignment revision with the devices resolved from the profile scope. When
    they differ, it creates a new revision containing PRESENT and ABSENT rows,
    then publishes the resulting changes. Delivery metadata is updated on the
    revision, but assignment history is never deleted or replaced.
    """

    def __init__(self, repo: ProfileRepository, producer: RabbitMQProducer) -> None:
        self.repo = repo
        self.producer = producer

    async def recalculate_profile(
        self, profile_id: int, *, force_push: bool = False, publish: bool = True
    ) -> None:
        """Create and optionally publish the next assignment revision.

        ``publish=False`` is used during device check-in: it updates desired
        state first, while ``reconcile_device`` sends only the latest state once.
        """
        # Lock before reading assignments or resolving the scope. Two concurrent
        # recalculations must not both diff against the same stale assignment set.
        profile = await self.repo.get_by_id_for_update(profile_id)
        if not profile:
            return

        current_ids = await self.repo.get_current_desired_device_ids(profile_id)
        resolved = await self._resolve_scope(profile.scope) if profile.scope.targets else {}
        assignments = AssignmentCalculator.compute(
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

        latest_version = await self.repo.get_max_assignment_version(profile_id)
        version = max(profile.version, latest_version + 1 if latest_version else 1)
        profile.version = version
        # Keep every revision. ABSENT rows represent revocations that must also
        # be delivered and provide an audit trail for the previous assignment.
        await self.repo.bulk_create_assignments(
            profile_id,
            version,
            desired_ids,
            revoked_device_ids=revoked_ids,
        )
        await self.repo.db.commit()

        if not publish:
            return

        push_ids = desired_ids if force_push else new_ids
        current_assignments = await self.repo.get_current_assignments(profile_id)
        present_assignments = {
            assignment.device_id: assignment
            for assignment in current_assignments
            if assignment.profile_version == version
            and assignment.desired_state == AssignmentDesiredState.PRESENT
        }
        absent_assignments = {
            assignment.device_id: assignment
            for assignment in current_assignments
            if assignment.profile_version == version
            and assignment.desired_state == AssignmentDesiredState.ABSENT
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

    async def recalculate_for_device(
        self, device_id: int, *, publish: bool = True
    ) -> None:
        profiles = await self.repo.list_affected_profiles_for_device(device_id)
        for profile in profiles:
            await self.recalculate_profile(profile.id, publish=publish)

    async def recalculate_for_smart_group(self, group_id: int) -> None:
        for profile in await self.repo.list_all_profiles():
            scope = profile.scope
            if any(
                target.scope_type == ScopeType.SMART_GROUP
                and target.target_id == group_id
                for target in scope.targets
            ) or any(
                exclusion.scope_type == ScopeType.SMART_GROUP
                and exclusion.exclude_id == group_id
                for exclusion in scope.exclusions
            ):
                await self.recalculate_profile(profile.id)

    async def recalculate_for_static_group(self, group_id: int) -> None:
        for profile in await self.repo.list_all_profiles():
            scope = profile.scope
            if any(
                target.scope_type == ScopeType.STATIC_GROUP
                and target.target_id == group_id
                for target in scope.targets
            ) or any(
                exclusion.scope_type == ScopeType.STATIC_GROUP
                and exclusion.exclude_id == group_id
                for exclusion in scope.exclusions
            ):
                await self.recalculate_profile(profile.id)

    async def reconcile_device(self, device_id: int) -> None:
        """Send the latest desired profile state to an enrolled device check-in."""
        device = await self.repo.db.get(Device, device_id)
        if device is None or device.status != DeviceStatus.ENROLLED:
            return

        assignments = await self.repo.get_current_assignments_for_device(device_id)
        for assignment in assignments:
            profile = await self.repo.get_by_id(assignment.profile_id)
            if profile is None:
                continue
            try:
                if assignment.desired_state == AssignmentDesiredState.PRESENT:
                    message_id = await self.producer.publish_profile_push(
                        device_id=device_id,
                        profile_id=profile.id,
                        profile_config=profile.settings,
                        profile_version=assignment.profile_version,
                        assignment_id=assignment.id,
                    )
                else:
                    message_id = await self.producer.publish_profile_revoke(
                        device_id=device_id,
                        profile_id=profile.id,
                        profile_version=assignment.profile_version,
                        assignment_id=assignment.id,
                    )
                await self.repo.mark_assignment_sent(assignment.id, message_id)
            except Exception as exc:
                await self.repo.mark_assignment_failed(assignment.id, str(exc))

    async def _resolve_scope(self, scope: Scope) -> dict[tuple[str, int], set[int]]:
        result: dict[tuple[str, int], set[int]] = {}

        for target in scope.targets:
            device_ids = await self._resolve_target(target)
            if device_ids:
                key = (target.scope_type.value, target.target_id or 0)
                result.setdefault(key, set()).update(device_ids)

        for exclusion in scope.exclusions:
            device_ids = await self._resolve_exclusion(exclusion)
            if device_ids:
                key = (exclusion.scope_type.value, exclusion.exclude_id or 0)
                result.setdefault(key, set()).update(device_ids)

        return result

    async def _resolve_target(self, target: Target) -> set[int]:
        db = self.repo.db

        if target.scope_type == ScopeType.ALL_DEVICES:
            stmt = select(Device.id).where(Device.status == DeviceStatus.ENROLLED)
            rows = await db.execute(stmt)
            return {row[0] for row in rows.all()}

        if target.scope_type == ScopeType.SMART_GROUP and target.target_id:
            return await self._resolve_smart_group(target.target_id)

        if target.scope_type == ScopeType.STATIC_GROUP and target.target_id:
            sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                StaticGroupDevice.static_group_id == target.target_id
            )
            sg_dev_result = await db.execute(sg_dev_stmt)
            serial_numbers = {row[0] for row in sg_dev_result.all()}
            if not serial_numbers:
                return set()
            dev_stmt = select(Device.id).where(
                Device.serial_number.in_(serial_numbers),
                Device.status == DeviceStatus.ENROLLED,
            )
            dev_result = await db.execute(dev_stmt)
            return {row[0] for row in dev_result.all()}

        if target.scope_type == ScopeType.DEVICE and target.target_id:
            device_result = await db.execute(
                select(Device.id).where(
                    Device.id == target.target_id,
                    Device.status == DeviceStatus.ENROLLED,
                )
            )
            device_id = device_result.scalar_one_or_none()
            return {device_id} if device_id is not None else set()

        return set()

    async def _resolve_exclusion(self, exclusion: Exclusion) -> set[int]:
        db = self.repo.db

        if exclusion.scope_type == ScopeType.DEVICE and exclusion.exclude_id:
            return {exclusion.exclude_id}

        if exclusion.scope_type == ScopeType.SMART_GROUP and exclusion.exclude_id:
            return await self._resolve_smart_group(exclusion.exclude_id)

        if exclusion.scope_type == ScopeType.STATIC_GROUP and exclusion.exclude_id:
            sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                StaticGroupDevice.static_group_id == exclusion.exclude_id
            )
            sg_dev_result = await db.execute(sg_dev_stmt)
            serial_numbers = {row[0] for row in sg_dev_result.all()}
            if not serial_numbers:
                return set()
            dev_stmt = select(Device.id).where(
                Device.serial_number.in_(serial_numbers),
                Device.status == DeviceStatus.ENROLLED,
            )
            dev_result = await db.execute(dev_stmt)
            return {row[0] for row in dev_result.all()}

        return set()

    async def _resolve_smart_group(self, group_id: int) -> set[int]:
        result = await self.repo.db.execute(
            select(SmartGroup).where(SmartGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        if not group or not isinstance(group.criteria, list):
            return set()

        criteria = [Criteria.model_validate(item) for item in group.criteria]
        where = build_device_query(criteria)
        stmt = select(Device.id).where(Device.status == DeviceStatus.ENROLLED)
        if where is not None:
            stmt = stmt.where(where)
        result = await self.repo.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def _send_push_messages(
        self,
        profile: Profile,
        device_ids: set[int],
        assignments: dict[int, ProfileAssignment],
        version: int,
    ) -> None:
        for device_id in sorted(device_ids):
            assignment = assignments.get(device_id)
            try:
                message_id = await self.producer.publish_profile_push(
                    device_id=device_id,
                    profile_id=profile.id,
                    profile_config=profile.settings,
                    profile_version=version,
                    assignment_id=assignment.id if assignment else None,
                )
                if assignment:
                    await self.repo.mark_assignment_sent(assignment.id, message_id)
            except Exception as exc:
                if assignment:
                    await self.repo.mark_assignment_failed(assignment.id, str(exc))
                logger.exception(
                    "Failed to send push for profile %s to device %s",
                    profile.id,
                    device_id,
                )

    async def _send_revoke_messages(
        self,
        profile: Profile,
        device_ids: set[int],
        assignments: dict[int, ProfileAssignment],
        version: int,
    ) -> None:
        for device_id in sorted(device_ids):
            assignment = assignments.get(device_id)
            try:
                message_id = await self.producer.publish_profile_revoke(
                    device_id=device_id,
                    profile_id=profile.id,
                    profile_version=version,
                    assignment_id=assignment.id if assignment else None,
                )
                if assignment:
                    await self.repo.mark_assignment_sent(assignment.id, message_id)
            except Exception as exc:
                if assignment:
                    await self.repo.mark_assignment_failed(assignment.id, str(exc))
                logger.exception(
                    "Failed to send revoke for profile %s to device %s",
                    profile.id,
                    device_id,
                )
