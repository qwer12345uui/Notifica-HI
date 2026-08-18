#!/usr/bin/env python3
"""Static verification for the Notifica 1.0.6 compatibility release."""

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
    require(info["CFBundleShortVersionString"] == "1.0.6", "preference bundle version matches compatibility release")
    require("bundle = NotificaPrefs;" in entry, "PreferenceLoader points to the preference bundle")
    require("detail = NTFPrefsListController;" in entry, "PreferenceLoader points to the main controller")
    require("isController = 1;" in entry, "PreferenceLoader marks the entry as a controller")

    tweak = read("Tweak/Tweak.xm")
    require("dpkgInvalid" not in tweak, "runtime activation has no rootful package-database gate")
    require("NotificaSB" not in tweak, "obsolete package-source alert group is removed")
    require(tweak.count('enabled = [([file objectForKey:@"Enabled"] ?: @(YES)) boolValue];') == 2,
            "SpringBoard and widget processes both use the Enabled preference")

    injection_filter = read("Tweak/Notifica.plist")
    require("com.apple.springboard" in injection_filter, "tweak is limited to SpringBoard")
    require("com.apple.UIKit" not in injection_filter, "tweak no longer injects into all UIKit applications")
    require("com.apple.Preferences" not in injection_filter, "tweak is not injected into Settings")

    for makefile in ("Tweak/Makefile", "Prefs/Makefile"):
        require("TARGET = iphone:clang:latest:15.0" in read(makefile), f"{makefile} targets iOS 15.0")

    control = read("control")
    require("Version: 1.0.6" in control, "package version matches compatibility release")

    workflow = read(".github/workflows/build-notifica-rh.yml")
    require("THEOS_PACKAGE_SCHEME=roothide" in workflow, "workflow builds the RootHide package scheme")
    require("actions/upload-artifact@v4" in workflow, "workflow uploads the generated package")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, plistlib.InvalidFileException) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1)
