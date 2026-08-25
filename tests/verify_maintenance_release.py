#!/usr/bin/env python3
"""Static verification for the Notifica 1.0.10 arm64e preferences compatibility release."""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> None:
    with (ROOT / "Prefs/Resources/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    entry = read("Prefs/entry.plist")

    require(info["CFBundleExecutable"] == "NotificaPrefs", "preference bundle executable is declared")
    require(info["NSPrincipalClass"] == "NTFPrefsListController", "preference bundle principal class is declared")
    require(info["CFBundleIdentifier"] == "com.rpgfarm.notifica.preferences", "preference bundle identifier is stable")
    require(info["CFBundleShortVersionString"] == "1.0.10", "preference bundle version matches preferences compatibility release")
    require("bundle = NotificaPrefs;" in entry, "PreferenceLoader points to the preference bundle")
    require("detail = NTFPrefsListController;" in entry, "PreferenceLoader points to the main controller")
    require("isController = 1;" in entry, "PreferenceLoader marks the entry as a controller")

    tweak = read("Tweak/Tweak.xm")
    require("dpkgInvalid" not in tweak, "runtime activation has no rootful package-database gate")
    require("operatingSystemVersion" in tweak, "runtime reads the structured iOS version")
    require("systemVersion.majorVersion < 15 || systemVersion.majorVersion > 17" in tweak,
            "runtime explicitly guards the supported iOS 15–17 range")
    require("NSClassFromString(@\"WGWidgetPlatterView\")" in tweak,
            "legacy widget hook is only loaded when its class exists")
    require("NotificaSB" not in tweak, "obsolete package-source alert group is removed")
    require(tweak.count('enabled = [([file objectForKey:@"Enabled"] ?: @(YES)) boolValue];') == 2,
            "SpringBoard and widget processes both use the Enabled preference")

    injection_filter = read("Tweak/Notifica.plist")
    require("com.apple.springboard" in injection_filter, "tweak is limited to SpringBoard")
    require("com.apple.UIKit" not in injection_filter, "tweak no longer injects into all UIKit applications")
    require("com.apple.Preferences" not in injection_filter, "tweak is not injected into Settings")

    tweak_makefile = read("Tweak/Makefile")
    prefs_makefile = read("Prefs/Makefile")
    for path, makefile in (("Tweak/Makefile", tweak_makefile), ("Prefs/Makefile", prefs_makefile)):
        require("TARGET = iphone:clang:latest:15.0" in makefile, f"{path} targets iOS 15.0")
        require("_LIBRARIES" in makefile and "root" in makefile, f"{path} declares a non-rootful path library")

    require("THEOS_PACKAGE_SCHEME),roothide" in tweak_makefile, "tweak retains a Roothide framework rpath")
    prefs_header = read("Prefs/Preferences.h")
    prefs_implementation = read("Prefs/Preferences.m")
    require("#import <rootless.h>" in prefs_header, "preferences retain standard rootless path macros")
    require("#import <roothide.h>" in prefs_header, "preferences import the official Roothide path API")
    require("NTF_ROOTHIDE_BUILD" in prefs_makefile, "Roothide build selects its official path API")
    require("roothide" in prefs_makefile, "Roothide preferences link libroothide")
    require("NTF_JB_PATH_NS(@\"/usr/bin/killall\")" in prefs_implementation,
            "respring command uses a rootless and Roothide-safe path")

    prefs_runtime = "\n".join([
        read("Prefs/Makefile"),
        read("Prefs/Preferences.h"),
        read("Prefs/Preferences.m"),
        read("Prefs/NTFSubPrefsListController.h"),
        read("Prefs/SavedSettings.h"),
        read("Prefs/SavedSettings.m"),
    ])
    require("Cephei" not in prefs_runtime, "preference bundle has no Cephei runtime dependency")
    require("HBPreferences" not in prefs_runtime, "preference bundle uses system preference storage")
    require("NTFPreferencesStore" in prefs_runtime, "preference bundle reads the existing Notifica preference domain")

    with (ROOT / "Prefs/Resources/Prefs.plist").open("rb") as stream:
        main_specifier_plist = plistlib.load(stream)
    main_specifiers = read("Prefs/Resources/Prefs.plist")
    require(isinstance(main_specifier_plist.get("items"), list), "main settings plist has a valid items array")
    for custom_cell in ("HBImageTableCell", "HBTwitterCell", "HBLinkTableCell"):
        require(custom_cell not in main_specifiers, f"main settings page does not require {custom_cell}")
    require("PSLinkCell" in main_specifiers, "main settings page uses native navigation cells")

    control = read("control")
    require("Version: 1.0.10" in control, "package version matches preferences compatibility release")

    workflow = read(".github/workflows/build-notifica-rh.yml")
    require("runs-on: macos-13" in workflow, "workflow builds final arm64e bundles with macOS Xcode")
    require("Confirm Xcode arm64e toolchain" in workflow,
            "workflow verifies the macOS arm64e build toolchain")
    require("rootless" in workflow, "workflow builds the standard rootless package scheme")
    require("roothide" in workflow, "workflow builds the Roothide package scheme")
    require("THEOS_PACKAGE_SCHEME=${{ matrix.scheme }}" in workflow,
            "workflow passes each package scheme to Theos")
    require("verify_package_layout.sh packages" in workflow,
            "workflow validates each emitted DEB before upload")
    require("actions/upload-artifact@v4" in workflow, "workflow uploads both generated packages")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, plistlib.InvalidFileException, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
