import logging

from sqlalchemy import select

from app.common.schemas import Exclusion, Scope, ScopeType, Target
from app.criteria import build_device_query
from app.criteria.schemas import Criteria
from app.devices.models import Device
from app.messaging.producer import RabbitMQProducer
from app.profiles.calculator import AssignmentCalculator
from app.profiles.models import Profile
from app.profiles.repositories import ProfileRepository
from app.static_groups.models import StaticGroupDevice

logger = logging.getLogger(__name__)


class Recalculator:
    def __init__(self, repo: ProfileRepository, producer: RabbitMQProducer) -> None:
        self.repo = repo
        self.producer = producer

    async def recalculate_profile(self, profile_id: int) -> None:
        profile = await self.repo.get_by_id(profile_id)
        if not profile:
            return

        if not profile.scope.targets:
            max_version = await self.repo.get_max_assignment_version(profile_id)
            if max_version > 0:
                await self.repo.delete_assignments_at_version(profile_id, max_version)
            return

        max_version = await self.repo.get_max_assignment_version(profile_id)
        current_ids = await self.repo.get_assignment_device_ids_at_version(
            profile_id, max_version
        ) if max_version > 0 else set()

        resolved = await self._resolve_scope(profile.scope)
        assignments = AssignmentCalculator.compute(
            profile_id=profile_id,
            profile_version=max_version or 1,
            scope=profile.scope,
            resolved_device_ids=resolved,
        )
        desired_ids = {a.device_id for a in assignments}

        new_ids = desired_ids - current_ids
        revoked_ids = current_ids - desired_ids

        if not new_ids and not revoked_ids:
            return

        if max_version > 0:
            await self.repo.delete_assignments_at_version(profile_id, max_version)

        version = max_version or 1
        await self.repo.db.execute(
            select(Profile).where(Profile.id == profile_id).with_for_update()
        )
        await self.repo.bulk_create_assignments(profile_id, version, desired_ids)
        await self.repo.db.commit()

        if new_ids:
            await self._send_push_messages(profile, new_ids)
        if revoked_ids:
            await self._send_revoke_messages(profile, revoked_ids)

    async def recalculate_for_device(self, device_id: int) -> None:
        profiles = await self.repo.list_all_profiles()
        for profile in profiles:
            if profile.scope.targets:
                await self.recalculate_profile(profile.id)

    async def _resolve_scope(self, scope: Scope) -> dict[tuple[str, int], set[int | str]]:
        result: dict[tuple[str, int], set[int | str]] = {}

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
            stmt = select(Device.id)
            rows = await db.execute(stmt)
            return {row[0] for row in rows.all()}

        if target.scope_type == ScopeType.SMART_GROUP and target.target_id:
            from app.smart_groups.models import SmartGroup

            sg_result = await db.execute(
                select(SmartGroup).where(SmartGroup.id == target.target_id)
            )
            smart_group = sg_result.scalar_one_or_none()
            if not smart_group or not smart_group.criteria:
                return set()
            criteria_list = (
                [Criteria.model_validate(c) for c in smart_group.criteria]
                if isinstance(smart_group.criteria, list)
                else []
            )
            where = build_device_query(criteria_list)
            dev_stmt = select(Device.id).where(where) if where is not None else select(Device.id)
            dev_result = await db.execute(dev_stmt)
            return {row[0] for row in dev_result.all()}

        if target.scope_type == ScopeType.STATIC_GROUP and target.target_id:
            sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                StaticGroupDevice.static_group_id == target.target_id
            )
            sg_dev_result = await db.execute(sg_dev_stmt)
            serial_numbers = {row[0] for row in sg_dev_result.all()}
            if not serial_numbers:
                return set()
            dev_stmt = select(Device.id).where(
                Device.serial_number.in_(serial_numbers)
            )
            dev_result = await db.execute(dev_stmt)
            return {row[0] for row in dev_result.all()}

        if target.scope_type == ScopeType.DEVICE and target.target_id:
            return {target.target_id}

        return set()

    async def _resolve_exclusion(self, exclusion: Exclusion) -> set[int]:
        db = self.repo.db

        if exclusion.scope_type == ScopeType.DEVICE and exclusion.exclude_id:
            return {exclusion.exclude_id}

        if exclusion.scope_type == ScopeType.SMART_GROUP and exclusion.exclude_id:
            from app.smart_groups.models import SmartGroup

            sg_result = await db.execute(
                select(SmartGroup).where(SmartGroup.id == exclusion.exclude_id)
            )
            smart_group = sg_result.scalar_one_or_none()
            if not smart_group or not smart_group.criteria:
                return set()
            criteria_list = (
                [Criteria.model_validate(c) for c in smart_group.criteria]
                if isinstance(smart_group.criteria, list)
                else []
            )
            where = build_device_query(criteria_list)
            dev_stmt = select(Device.id).where(where) if where is not None else select(Device.id)
            dev_result = await db.execute(dev_stmt)
            return {row[0] for row in dev_result.all()}

        if exclusion.scope_type == ScopeType.STATIC_GROUP and exclusion.exclude_id:
            sg_dev_stmt = select(StaticGroupDevice.device_serial_number).where(
                StaticGroupDevice.static_group_id == exclusion.exclude_id
            )
            sg_dev_result = await db.execute(sg_dev_stmt)
            serial_numbers = {row[0] for row in sg_dev_result.all()}
            if not serial_numbers:
                return set()
            dev_stmt = select(Device.id).where(
                Device.serial_number.in_(serial_numbers)
            )
            dev_result = await db.execute(dev_stmt)
            return {row[0] for row in dev_result.all()}

        return set()

    async def _send_push_messages(
        self, profile: Profile, device_ids: set[int]
    ) -> None:
        for device_id in sorted(device_ids):
            try:
                await self.producer.publish_profile_push(
                    device_id=device_id,
                    profile_id=profile.id,
                    profile_config=profile.settings,
                )
            except Exception:
                logger.exception(
                    "Failed to send push for profile %s to device %s",
                    profile.id,
                    device_id,
                )

    async def _send_revoke_messages(
        self, profile: Profile, device_ids: set[int]
    ) -> None:
        for device_id in sorted(device_ids):
            try:
                await self.producer.publish_profile_revoke(
                    device_id=device_id,
                    profile_id=profile.id,
                )
            except Exception:
                logger.exception(
                    "Failed to send revoke for profile %s to device %s",
                    profile.id,
                    device_id,
                )
