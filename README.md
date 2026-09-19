# Notifica

Notifica is a notification-customization tweak for jailbroken iOS. This maintenance branch preserves the original preference domain so that existing user settings continue to work while repairing the preference bundle metadata and eliminating a rootful-only package-database gate that prevented initialization on RootHide.

## Features

The tweak customizes notifications, banners, widgets, and Now Playing controls. It supports dark backgrounds and a modern visual style, and provides options for hiding header elements, centering content, changing transparency, corner radius, colors, blur, gradients, vertical positioning, and the “No older notifications” label. It also includes notification and banner test actions plus pull-to-clear behavior.

## Compatibility

| Item | Maintained configuration |
| --- | --- |
| Minimum deployment target | iOS 15.0 |
| Primary target range | iOS 15.x through iOS 16.x |
| Architectures | arm64 and arm64e (universal) |
| Roothide package scheme | `THEOS_PACKAGE_SCHEME=roothide` — hidden root, `iphoneos-arm64e` |
| Standard rootless package scheme | default scheme — `/var/jb`, `iphoneos-arm64` |

> Private SpringBoard classes can change between iOS point releases. Test a feature on the intended device and iOS version before daily use. If a feature is ineffective on a specific iOS 16 release, disable that feature and report the device model, iOS version, and the affected setting instead of repeatedly forcing SpringBoard restarts.

## What was repaired

| Area | Repair |
| --- | --- |
| RootHide startup | Activation no longer depends on a rootful `/var/lib/dpkg` package-list path. The tweak now respects only its `Enabled` preference. |
| Preference bundle | Added `CFBundleExecutable`, `NSPrincipalClass`, a stable bundle identifier, and version metadata so Settings can load the main list controller. |
| Build configuration | Deployment target raised to iOS 15.0, `-std=c++14` scoped to Logos sources only, and a workflow that builds both the Roothide and standard rootless schemes on every push. |
| Settings stability | Restricts tweak injection to SpringBoard. The PreferenceBundle uses system Preferences APIs, has no Cephei runtime linkage, and its main page uses only native Preferences cells. |
| Versioning | Package and preference-bundle metadata identify this native settings release as `1.0.10`. |

## Build

Install RootHide Theos following the [RootHide developer documentation][1], then build either scheme with:

```sh
# Roothide, hidden root
make clean package FINALPACKAGE=1 THEOS_PACKAGE_SCHEME=roothide

# Standard rootless, installs under /var/jb
make clean package FINALPACKAGE=1
```

Both variants compile as universal `arm64` + `arm64e` binaries against the iOS 16.5 SDK with a deployment target of iOS 15.0. No third-party SDK download is required: RootHide Theos already vendors ABI-matched `Cephei.framework`, `libcolorpicker` and `libroothide` for each scheme.

## Continuous integration

Every push to `master`, and any manual dispatch, runs the **Build Notifica (Rootless and Roothide)** workflow on `macos-14`. It builds both schemes in parallel, asserts the emitted `.deb` payload and linkage, and publishes the packages to the `v1.0.10` release:

| Asset | Scheme | Architecture | Install root |
| --- | --- | --- | --- |
| `Notifica-rootless-iOS15-17.deb` | standard rootless | `iphoneos-arm64` | `/var/jb` |
| `Notifica-Roothide-iOS15-17.deb` | Roothide hidden root | `iphoneos-arm64e` | hidden root, resolved through `@loader_path/.jbroot` |

The two packages declare the same identifier (`com.rpgfarm.notifica`) and differ only in install root and architecture, so install just the one that matches your jailbreak.

If a build fails, the workflow attaches the complete `make` output for both schemes as `build-<scheme>.log` to the `ci-failure` release, so the failure is diagnosable without an authenticated Actions session.

## Test matrix

The intended primary test target is an **iPhone Xs Max** (`iPhone11,6`, A12) or **iPhone 13 Pro Max** (`iPhone14,3`, A15) running iOS 15.0 with RootHide Dopamine. Validate the following separately: opening the Notifica Settings page, changing a preference and respringing, testing a banner, testing a notification, opening a widget, and enabling/disabling each major feature group. Keep ordinary package-manager/install/respring checks separate from any extended device stability testing.

## Artwork notice

This personal-use maintenance build may include artwork extracted from a user-supplied original Notifica package. Do not publish or redistribute that artwork without permission from the original author or rightsholder.

## References

[1]: https://github.com/roothide/Developer "RootHide developer documentation"
