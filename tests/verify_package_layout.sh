#!/usr/bin/env bash
# Verify the package emitted by Theos for the active non-rootful scheme.
set -euo pipefail

package_dir="${1:-packages}"
scheme="${THEOS_PACKAGE_SCHEME:?THEOS_PACKAGE_SCHEME must be rootless or roothide}"
if [[ -n "${OTOOL:-}" ]]; then
  otool_bin="${OTOOL}"
elif [[ "$(uname)" == "Darwin" ]]; then
  otool_bin="$(command -v otool)"
else
  otool_bin="${THEOS:?THEOS must be set}/toolchain/linux/iphone/bin/otool"
fi

case "${scheme}" in
  rootless)
    expected_arch="iphoneos-arm64"
    expected_prefix="var/jb/Library"
    ;;
  roothide)
    expected_arch="iphoneos-arm64e"
    expected_prefix="Library"
    expected_dependency="libroothide.dylib"
    ;;
  *)
    echo "FAIL: unsupported package scheme: ${scheme}" >&2
    exit 2
    ;;
esac

shopt -s nullglob
packages=("${package_dir}"/*.deb)
if [[ ${#packages[@]} -ne 1 ]]; then
  echo "FAIL: expected exactly one DEB in ${package_dir}, found ${#packages[@]}" >&2
  exit 1
fi

deb="${packages[0]}"
workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

dpkg-deb --field "${deb}" Package Version Architecture > "${workdir}/control"
grep -qx 'Package: com.rpgfarm.notifica' "${workdir}/control"
grep -qx 'Version: 1.0.10' "${workdir}/control"
grep -qx "Architecture: ${expected_arch}" "${workdir}/control"

dpkg-deb --contents "${deb}" > "${workdir}/contents"
grep -q " ${expected_prefix}/MobileSubstrate/DynamicLibraries/Notifica.dylib$" "${workdir}/contents"
grep -q " ${expected_prefix}/PreferenceBundles/NotificaPrefs.bundle/NotificaPrefs$" "${workdir}/contents"
grep -q 'Library/PreferenceLoader/Preferences/NotificaPrefs.plist$' "${workdir}/contents"

dpkg-deb --extract "${deb}" "${workdir}/payload"
tweak="${workdir}/payload/${expected_prefix}/MobileSubstrate/DynamicLibraries/Notifica.dylib"
prefs="${workdir}/payload/${expected_prefix}/PreferenceBundles/NotificaPrefs.bundle/NotificaPrefs"

for binary in "${tweak}" "${prefs}"; do
  file "${binary}" | grep -q 'arm64'
  file "${binary}" | grep -q 'arm64e'
done

"${otool_bin}" -L "${tweak}" > "${workdir}/tweak-linkage"
if [[ "${scheme}" == "roothide" ]]; then
  grep -q 'libroothide.dylib' "${workdir}/tweak-linkage"
  grep -q '@loader_path/.jbroot/Library/Frameworks/Cephei.framework/Cephei' "${workdir}/tweak-linkage"
else
  # Standard rootless links libroot statically; Cephei remains an @rpath framework.
  grep -q '@rpath/Cephei.framework/Cephei' "${workdir}/tweak-linkage"
fi

echo "PASS: ${scheme} package metadata, payload layout, universal binaries, and dependency paths are valid"
