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

# macOS has no dpkg-deb. A .deb is just an `ar` archive holding control.tar.*
# and data.tar.*, so fall back to ar + tar when the Debian tooling is absent.
dpkg_deb_bin="$(command -v dpkg-deb || true)"

die() { echo "FAIL: $*" >&2; exit 1; }

# Print the haystack alongside the needle whenever an assertion fails; a bare
# non-zero grep tells you nothing in a CI log.
require_line() {
  local pattern="$1" haystack="$2" what="$3"
  if grep -qE "${pattern}" "${haystack}"; then
    return 0
  fi
  echo "FAIL: ${what} — no line matching ${pattern} in ${haystack}" >&2
  sed 's/^/    | /' "${haystack}" >&2
  exit 1
}

unpack_deb() {
  local deb="$1" dir="$2"
  mkdir -p "${dir}/payload" "${dir}/control_dir"

  if [[ -n "${dpkg_deb_bin}" ]]; then
    "${dpkg_deb_bin}" --extract "${deb}" "${dir}/payload"
    "${dpkg_deb_bin}" --control "${deb}" "${dir}/control_dir"
    "${dpkg_deb_bin}" --field "${deb}" > "${dir}/control"
    "${dpkg_deb_bin}" --contents "${deb}" > "${dir}/contents"
    return 0
  fi

  local ardir="${dir}/ar"
  mkdir -p "${ardir}"
  (cd "${ardir}" && ar -x "${deb}") || die "cannot unpack ${deb} with ar"

  local control_member="" data_member=""
  for candidate in "${ardir}"/control.tar.*; do
    [[ -f "${candidate}" ]] || continue
    control_member="${candidate}"
    break
  done
  for candidate in "${ardir}"/data.tar.*; do
    [[ -f "${candidate}" ]] || continue
    data_member="${candidate}"
    break
  done
  [[ -n "${control_member}" ]] || die "${deb} has no control.tar.* member"
  [[ -n "${data_member}" ]] || die "${deb} has no data.tar.* member"

  tar -xf "${control_member}" -C "${dir}/control_dir"
  tar -xf "${data_member}" -C "${dir}/payload"
  tar -tf "${data_member}" > "${dir}/contents"

  if [[ -f "${dir}/control_dir/control" ]]; then
    cat "${dir}/control_dir/control" > "${dir}/control"
  else
    for candidate in "${dir}/control_dir"/control*; do
      [[ -f "${candidate}" ]] || continue
      cat "${candidate}" > "${dir}/control"
      break
    done
  fi
  [[ -s "${dir}/control" ]] || die "${deb} has no control file"
}

deb="${packages[0]}"
workdir="$(mktemp -d)"
trap 'rm -rf "${workdir}"' EXIT

unpack_deb "${deb}" "${workdir}"

require_line '^Package: com[.]rpgfarm[.]notifica([[:space:]]|$)' "${workdir}/control" 'package identifier'
require_line '^Version: 1[.]0[.]10([[:space:]]|$)' "${workdir}/control" 'package version'
require_line "^Architecture: ${expected_arch}([[:space:]]|$)" "${workdir}/control" 'package architecture'

# The payload listing is `tar -tf`-style: the path sits in the last field, so it
# starts after whitespace rather than at column 0 or after a slash. Anchor on
# whitespace on both ends so archives that store `./Library/...` still match.
require_line "(^|[[:space:]])${expected_prefix}/MobileSubstrate/DynamicLibraries/Notifica[.]dylib([[:space:]]|$)" \
  "${workdir}/contents" 'tweak dylib payload path'
require_line "(^|[[:space:]])${expected_prefix}/PreferenceBundles/NotificaPrefs[.]bundle/NotificaPrefs([[:space:]]|$)" \
  "${workdir}/contents" 'preferences bundle payload path'
require_line '(^|[[:space:]])Library/PreferenceLoader/Preferences/NotificaPrefs[.]plist([[:space:]]|$)' \
  "${workdir}/contents" 'preference loader entry plist'

tweak="${workdir}/payload/${expected_prefix}/MobileSubstrate/DynamicLibraries/Notifica.dylib"
prefs="${workdir}/payload/${expected_prefix}/PreferenceBundles/NotificaPrefs.bundle/NotificaPrefs"

for binary in "${tweak}" "${prefs}"; do
  [[ -f "${binary}" ]] || die "missing payload binary: ${binary}"
  file "${binary}" | grep -q 'arm64' || die "${binary} has no arm64 slice"
  file "${binary}" | grep -q 'arm64e' || die "${binary} has no arm64e slice"
done

"${otool_bin}" -L "${tweak}" > "${workdir}/tweak-linkage"
if [[ "${scheme}" == "roothide" ]]; then
  require_line 'libroothide[.]dylib' "${workdir}/tweak-linkage" 'libroothide linkage'
  require_line '@loader_path/[.]jbroot/Library/Frameworks/Cephei[.]framework/Cephei' \
    "${workdir}/tweak-linkage" 'jbroot-relative Cephei linkage'
else
  # Standard rootless links libroot statically; Cephei remains an @rpath framework.
  require_line '@rpath/Cephei[.]framework/Cephei' "${workdir}/tweak-linkage" 'Cephei linkage'
fi

echo "PASS: ${scheme} package metadata, payload layout, universal binaries, and dependency paths are valid"
