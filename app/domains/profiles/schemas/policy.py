from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from pydantic import BaseModel


class BluetoothSharing(IntEnum):
    BLUETOOTH_SHARING_UNSPECIFIED = 0
    BLUETOOTH_SHARING_ALLOWED = 1
    BLUETOOTH_SHARING_DISALLOWED = 2


class CameraAccess(IntEnum):
    CAMERA_ACCESS_UNSPECIFIED = 0
    CAMERA_ACCESS_USER_CHOICE = 1
    CAMERA_ACCESS_DISABLED = 2
    CAMERA_ACCESS_ENFORCED = 3


class ConfigureWifi(IntEnum):
    CONFIGURE_WIFI_UNSPECIFIED = 0
    ALLOW_CONFIGURING_WIFI = 1
    DISALLOW_ADD_WIFI_CONFIG = 2
    DISALLOW_CONFIGURING_WIFI = 3


class LocationMode(IntEnum):
    LOCATION_MODE_UNSPECIFIED = 0
    LOCATION_USER_CHOICE = 1
    LOCATION_ENFORCED = 2
    LOCATION_DISABLED = 3


class InstallType(IntEnum):
    INSTALL_TYPE_UNSPECIFIED = 0
    PREINSTALLED = 1
    FORCE_INSTALLED = 2
    BLOCKED = 3
    AVAILABLE = 4
    REQUIRED_FOR_SETUP = 5
    CUSTOM = 7


class PermissionPolicy(IntEnum):
    PERMISSION_POLICY_UNSPECIFIED = 0
    PROMPT = 1
    GRANT = 2
    DENY = 3


class TetheringSettings(IntEnum):
    TETHERING_SETTINGS_UNSPECIFIED = 0
    ALLOW_ALL_TETHERING = 1
    DISALLOW_WIFI_TETHERING = 2
    DISALLOW_ALL_TETHERING = 3


class UsbDataAccess(IntEnum):
    USB_DATA_ACCESS_UNSPECIFIED = 0
    ALLOW_USB_DATA_TRANSFER = 1
    DISALLOW_USB_FILE_TRANSFER = 2
    DISALLOW_USB_DATA_TRANSFER = 3


class WifiDirectSettings(IntEnum):
    WIFI_DIRECT_SETTINGS_UNSPECIFIED = 0
    ALLOW_WIFI_DIRECT = 1
    DISALLOW_WIFI_DIRECT = 2


class WifiRoamingMode(IntEnum):
    WIFI_ROAMING_MODE_UNSPECIFIED = 0
    DISABLED = 1
    DEFAULT = 2
    AGGRESSIVE = 3


class WifiSsidPolicyType(IntEnum):
    WIFI_SSID_POLICY_TYPE_UNSPECIFIED = 0
    WIFI_SSID_DENYLIST = 1
    WIFI_SSID_ALLOWLIST = 2


class WipeDataFlag(IntEnum):
    WIPE_DATA_FLAG_UNSPECIFIED = 0
    WIPE_ESIMS = 1


class AutoDateAndTimeZone(IntEnum):
    AUTO_DATE_AND_TIME_ZONE_UNSPECIFIED = 0
    USER_CHOICE = 1
    ENFORCED = 2


class UntrustedAppsPolicy(IntEnum):
    UNTRUSTED_APPS_POLICY_UNSPECIFIED = 0
    DISALLOW_INSTALL = 1
    ALLOW_INSTALL_IN_PERSONAL_PROFILE_ONLY = 2
    ALLOW_INSTALL_DEVICE_WIDE = 3


class DeveloperSettings(IntEnum):
    DEVELOPER_SETTINGS_UNSPECIFIED = 0
    DEVELOPER_SETTINGS_DISABLED = 1
    DEVELOPER_SETTINGS_ALLOWED = 2


class KeyguardDisabledFeature(IntEnum):
    KEYGUARD_DISABLED_FEATURE_UNSPECIFIED = 0
    CAMERA = 1
    NOTIFICATIONS = 2
    UNREDACTED_NOTIFICATIONS = 3
    TRUST_AGENTS = 4
    DISABLE_FINGERPRINT = 5
    DISABLE_REMOTE_INPUT = 6
    FACE = 7
    IRIS = 8
    BIOMETRICS = 9
    SHORTCUTS = 10
    ALL_FEATURES = 11


class AirplaneModeState(IntEnum):
    AIRPLANE_MODE_STATE_UNSPECIFIED = 0
    AIRPLANE_MODE_USER_CHOICE = 1
    AIRPLANE_MODE_DISABLED = 2


class UltraWidebandState(IntEnum):
    ULTRA_WIDEBAND_STATE_UNSPECIFIED = 0
    ULTRA_WIDEBAND_USER_CHOICE = 1
    ULTRA_WIDEBAND_DISABLED = 2


class CellularTwoGState(IntEnum):
    CELLULAR_TWO_G_STATE_UNSPECIFIED = 0
    CELLULAR_TWO_G_USER_CHOICE = 1
    CELLULAR_TWO_G_DISABLED = 2


class MicrophoneAccess(IntEnum):
    MICROPHONE_ACCESS_UNSPECIFIED = 0
    MICROPHONE_ACCESS_USER_CHOICE = 1
    MICROPHONE_ACCESS_DISABLED = 2
    MICROPHONE_ACCESS_ENFORCED = 3


class PrintingPolicy(IntEnum):
    PRINTING_POLICY_UNSPECIFIED = 0
    PRINTING_DISALLOWED = 1
    PRINTING_ALLOWED = 2


class MinimumWifiSecurityLevel(IntEnum):
    MINIMUM_WIFI_SECURITY_LEVEL_UNSPECIFIED = 0
    OPEN_NETWORK_SECURITY = 1
    PERSONAL_NETWORK_SECURITY = 2
    ENTERPRISE_NETWORK_SECURITY = 3
    ENTERPRISE_BIT192_NETWORK_SECURITY = 4


class UserInitiatedAddEsimSettings(IntEnum):
    USER_INITIATED_ADD_ESIM_SETTINGS_UNSPECIFIED = 0
    USER_INITIATED_ADD_ESIM_ALLOWED = 1
    USER_INITIATED_ADD_ESIM_DISALLOWED = 2


class WifiState(IntEnum):
    WIFI_STATE_UNSPECIFIED = 0
    WIFI_STATE_USER_CHOICE = 1
    WIFI_ENABLED = 2
    WIFI_DISABLED = 3


# ── Data classes ───────────────────────────────────────────────────────────


@dataclass
class ApplicationPolicy:
    packageName: str
    installType: InstallType | None = None
    defaultPermissionPolicy: PermissionPolicy | None = None
    permissionGrants: list[PermissionGrant] | None = None
    disabled: bool | None = None
    minimumVersionCode: int | None = None


@dataclass
class OpenNetworkConfiguration:
    networkConfigurations: list[NetworkConfiguration] | None = None
    certificates: list[NetworkCertificate] | None = None


@dataclass
class UserFacingMessage:
    defaultMessage: str
    localizedMessages: dict[str, str] | None = None


@dataclass
class NetworkConfiguration:
    guid: str
    name: str
    proxySettings: ProxySettings | None = None
    wifi: WiFi | None = None


@dataclass
class ProxySettings:
    type: str
    manual: Manual
    pac: str


@dataclass
class Manual:
    host: str
    port: int


@dataclass
class WiFi:
    ssid: str
    security: str
    hexSsid: str | None = None
    hiddenSsid: bool | None = None
    autoConnect: bool | None = None
    passphrase: str | None = None
    macAddressRandomizationMode: str | None = None
    eap: Eap | None = None


@dataclass
class Eap:
    outer: str | None = None
    inner: str | None = None
    identity: str | None = None
    anonymousIdentity: str | None = None
    domainSuffixMatch: list[str] | None = None
    serverCARefs: list[str] | None = None
    serverCaRef: str | None = None
    clientCertType: str | None = None
    clientCertRef: str | None = None
    clientCertKeyPairAlias: str | None = None


@dataclass
class NetworkCertificate:
    guid: str
    type: str
    x509: str
    remove: bool | None = None


@dataclass
class DeviceConnectivityManagement:
    usbDataAccess: UsbDataAccess | None = None
    configureWifi: ConfigureWifi | None = None
    wifiDirectSettings: WifiDirectSettings | None = None
    tetheringSettings: TetheringSettings | None = None
    wifiSsidPolicy: WifiSsidPolicy | None = None
    wifiRoamingPolicy: WifiRoamingPolicy | None = None
    bluetoothSharing: BluetoothSharing | None = None


@dataclass
class DeviceRadioState:
    wifiState: WifiState | None = None
    airplaneModeState: AirplaneModeState | None = None
    ultraWidebandState: UltraWidebandState | None = None
    cellularTwoGState: CellularTwoGState | None = None
    minimumWifiSecurityLevel: MinimumWifiSecurityLevel | None = None
    userInitiatedAddEsimSettings: UserInitiatedAddEsimSettings | None = None


@dataclass
class PermissionGrant:
    permission: str
    policy: PermissionPolicy


@dataclass
class WifiRoamingPolicy:
    wifiRoamingSettings: list[WifiRoamingSetting]


@dataclass
class WifiRoamingSetting:
    wifiSsid: str
    wifiRoamingMode: WifiRoamingMode


@dataclass
class WifiSsid:
    wifiSsid: str


@dataclass
class WifiSsidPolicy:
    wifiSsidPolicyType: WifiSsidPolicyType
    wifiSsids: list[WifiSsid]


@dataclass
class AdvancedSecurityOverrides:
    untrustedAppsPolicy: UntrustedAppsPolicy
    developerSettings: DeveloperSettings


class Policy(BaseModel):
    applications: list[ApplicationPolicy] | None = None
    screenCaptureDisabled: bool | None = None
    keyguardDisabledFeatures: list[KeyguardDisabledFeature] | None = None
    openNetworkConfiguration: OpenNetworkConfiguration | None = None
    addUserDisabled: bool | None = None
    adjustVolumeDisabled: bool | None = None
    factoryResetDisabled: bool | None = None
    installAppsDisabled: bool | None = None
    mountPhysicalMediaDisabled: bool | None = None
    modifyAccountsDisabled: bool | None = None
    uninstallAppsDisabled: bool | None = None
    statusBarDisabled: bool | None = None
    bluetoothContactSharingDisabled: bool | None = None
    shortSupportMessage: UserFacingMessage | None = None
    longSupportMessage: UserFacingMessage | None = None
    bluetoothConfigDisabled: bool | None = None
    cellBroadcastsConfigDisabled: bool | None = None
    credentialsConfigDisabled: bool | None = None
    mobileNetworksConfigDisabled: bool | None = None
    vpnConfigDisabled: bool | None = None
    networkResetDisabled: bool | None = None
    outgoingBeamDisabled: bool | None = None
    outgoingCallsDisabled: bool | None = None
    removeUserDisabled: bool | None = None
    shareLocationDisabled: bool | None = None
    smsDisabled: bool | None = None
    dataRoamingDisabled: bool | None = None
    locationMode: LocationMode | None = None
    bluetoothDisabled: bool | None = None
    permissionGrants: list[PermissionGrant] | None = None
    advancedSecurityOverrides: AdvancedSecurityOverrides | None = None
    autoDateAndTimeZone: AutoDateAndTimeZone | None = None
    cameraAccess: CameraAccess | None = None
    microphoneAccess: MicrophoneAccess | None = None
    deviceConnectivityManagement: DeviceConnectivityManagement | None = None
    deviceRadioState: DeviceRadioState | None = None
    printingPolicy: PrintingPolicy | None = None
    wipeDataFlags: list[WipeDataFlag] | None = None
