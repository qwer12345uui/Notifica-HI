# Notifica

Notifica is a notification-customization tweak for jailbroken iOS. This maintenance branch preserves the original preference domain so that existing user settings continue to work while repairing the preference bundle metadata and eliminating a rootful-only package-database gate that prevented initialization on RootHide.

## Features

The tweak customizes notifications, banners, widgets, and Now Playing controls. It supports dark backgrounds and a modern visual style, and provides options for hiding header elements, centering content, changing transparency, corner radius, colors, blur, gradients, vertical positioning, and the “No older notifications” label. It also includes notification and banner test actions plus pull-to-clear behavior.

## Compatibility

| Item | Maintained configuration |
| --- | --- |
| Minimum deployment target | iOS 15.0 |
| Primary target range | iOS 15.x through iOS 16.x |
| Architectures | arm64 and arm64e |
| Primary package scheme | RootHide (`THEOS_PACKAGE_SCHEME=roothide`) |
| Normal package scheme | Supported; omit `THEOS_PACKAGE_SCHEME` |

> Private SpringBoard classes can change between iOS point releases. Test a feature on the intended device and iOS version before daily use. If a feature is ineffective on a specific iOS 16 release, disable that feature and report the device model, iOS version, and the affected setting instead of repeatedly forcing SpringBoard restarts.

## What was repaired

| Area | Repair |
| --- | --- |
| RootHide startup | Activation no longer depends on a rootful `/var/lib/dpkg` package-list path. The tweak now respects only its `Enabled` preference. |
| Preference bundle | Added `CFBundleExecutable`, `NSPrincipalClass`, a stable bundle identifier, and version metadata so Settings can load the main list controller. |
| Build configuration | Updated the deployment target to iOS 15.0 and added a manually runnable RootHide build workflow. |
| Settings stability | Restricts tweak injection to SpringBoard so Settings and other UIKit applications do not load the Notifica tweak. The PreferenceBundle now uses system Preferences APIs and no longer links Cephei at page-load time. |
| Versioning | Package and preference-bundle metadata identify this stability release as `1.0.7`. |

## Build

Install RootHide Theos following the [RootHide developer documentation][1]. Then build a RootHide package with:

```sh
make clean package FINALPACKAGE=1 THEOS_PACKAGE_SCHEME=roothide
```

For a normal package, run the same command without `THEOS_PACKAGE_SCHEME=roothide`:

```sh
make clean package FINALPACKAGE=1
```

The **Build Notifica (RootHide)** workflow can also be started manually from the repository’s **Actions** page. It installs RootHide Theos, obtains the Cephei SDK, builds a RootHide package, and exposes the resulting `.deb` as a workflow artifact.

## Test matrix

The intended primary test target is an **iPhone Xs Max** (`iPhone11,6`, A12) or **iPhone 13 Pro Max** (`iPhone14,3`, A15) running iOS 15.0 with RootHide Dopamine. Validate the following separately: opening the Notifica Settings page, changing a preference and respringing, testing a banner, testing a notification, opening a widget, and enabling/disabling each major feature group. Keep ordinary package-manager/install/respring checks separate from any extended device stability testing.

## Artwork notice

This personal-use maintenance build may include artwork extracted from a user-supplied original Notifica package. Do not publish or redistribute that artwork without permission from the original author or rightsholder.

## References

[1]: https://github.com/roothide/Developer "RootHide developer documentation"
