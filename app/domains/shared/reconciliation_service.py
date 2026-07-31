from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.repositories import ProfileRepository
from app.domains.shared.scope import ScopeType
from app.infra.messaging.reconciliation import RecalculationKind, request_recalculation


class ReconciliationService:
    """Shared service for triggering profile and mobile app recalculation after domain writes."""

    def __init__(
        self,
        profile_repo: ProfileRepository,
        mobile_app_repo: MobileAppRepository,
    ) -> None:
        self.profile_repo = profile_repo
        self.mobile_app_repo = mobile_app_repo

    @staticmethod
    async def request_recalculate_profile(profile_id: int, *, force_push: bool = False) -> None:
        await request_recalculation(RecalculationKind.PROFILE, profile_id, force_push=force_push)

    @staticmethod
    async def request_recalculate_mobile_app(mobile_app_id: int, *, force_push: bool = False) -> None:
        await request_recalculation(RecalculationKind.MOBILE_APP, mobile_app_id, force_push=force_push)

    async def recalculate_profiles_for_device(self, device_id: int) -> None:
        for profile in await self.profile_repo.list_profiles_affected_by_device(device_id):
            await self.request_recalculate_profile(profile.id)

    async def recalculate_mobile_apps_for_device(self, device_id: int) -> None:
        for app in await self.mobile_app_repo.list_mobile_apps_affected_by_device(device_id):
            await self.request_recalculate_mobile_app(app.id)

    async def recalculate_profiles_for_group(self, scope_type: ScopeType, group_id: int) -> None:
        for profile in await self.profile_repo.list_profiles_referencing(scope_type, group_id):
            await self.request_recalculate_profile(profile.id)

    async def recalculate_mobile_apps_for_group(self, scope_type: ScopeType, group_id: int) -> None:
        for app in await self.mobile_app_repo.list_mobile_apps_referencing(scope_type, group_id):
            await self.request_recalculate_mobile_app(app.id)
