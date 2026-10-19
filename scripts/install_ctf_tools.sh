#!/usr/bin/env bash
# shellcheck disable=SC2024  # redirects target user-owned log file, not sudo
#
# install_ctf_tools.sh — CTF toolchain installer for the ctf-* skill library.
#
# This is a MERGED script. It takes the installer engine from the upstream
# project (ljagiello/ctf-skills: version pins, import-based skip checks, logging,
# venv handling for PEP 668, --dry-run/--force/--verify) and keeps the local
# additions from this fork (AI/ML packages, the wider apt/gem/go/manual lists,
# and the per-direction package annotations).
#
# Usage:
#   bash scripts/install_ctf_tools.sh [OPTIONS] MODE [MODE...]
#
# Modes:
#   python     pip packages (all platforms)
#   python-ai  the large AI/ML stack (torch, transformers, ...) — multi-GB
#   apt        Debian/Ubuntu system packages
#   brew       macOS Homebrew packages
#   gems       Ruby gems
#   go         Go tools
#   manual     Tools needing a manual/source install (prints instructions)
#   all        Every mode applicable to the current platform
#   --verify   Report which tools/modules are present vs missing, install nothing
#
# Options:
#   --dry-run  Show what would be installed without installing
#   --force    Reinstall packages even if already present
#
# Examples:
#   bash scripts/install_ctf_tools.sh all
#   bash scripts/install_ctf_tools.sh --dry-run all
#   bash scripts/install_ctf_tools.sh --force python
#   bash scripts/install_ctf_tools.sh --verify
#
# Recommended: pre-install before a competition. During a competition install only
# the direction you are working on, and timebox it.

set -uo pipefail

# Capture a DRY_RUN value passed via the environment BEFORE the globals below
# reset it: the README documents `DRY_RUN=1 bash scripts/install_ctf_tools.sh all`.
_DRY_RUN_FROM_ENV="${DRY_RUN:-}"

# --------------------------------------------------------------------------- #
# Globals
# --------------------------------------------------------------------------- #

# Honour DRY_RUN from the environment; the --dry-run flag can still enable it.
DRY_RUN=false
case "$_DRY_RUN_FROM_ENV" in
  1|true|yes|on) DRY_RUN=true ;;
esac
FORCE=false
LOG_DIR="${HOME}/.ctf-tools/logs"
LOG_FILE=""
CTF_VENV="${HOME}/.ctf-tools/venv"

FAILED=()
SUCCEEDED=()
SKIPPED=()

# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #

MODES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --force) FORCE=true; shift ;;
    --verify) MODES+=("--verify"); shift ;;
    -*) echo "Unknown option: $1" >&2; exit 2 ;;
    *) MODES+=("$1"); shift ;;
  esac
done
if [ "${#MODES[@]}" -eq 0 ]; then
  # No mode given. Historically this silently defaulted to "all", so a bare
  # invocation performed a full system install with no warning. Print usage
  # instead; `all` remains available explicitly.
  cat <<'USAGE'
usage: install_ctf_tools.sh [OPTIONS] MODE [MODE...]

Modes:
  python     pip packages (all platforms)
  python-ai  the large AI/ML stack (torch, transformers, ...) — multi-GB
  apt        Debian/Ubuntu system packages
  brew       macOS Homebrew packages
  gems       Ruby gems
  go         Go tools
  manual     tools needing a manual/source install (prints instructions)
  all        every mode applicable to the current platform
  --verify   report which tools/modules are present vs missing (installs nothing)

Options:
  --dry-run  show what would be installed without installing
  --force    reinstall packages even if already present

Examples:
  bash scripts/install_ctf_tools.sh all
  bash scripts/install_ctf_tools.sh --dry-run python
  DRY_RUN=1 bash scripts/install_ctf_tools.sh python
  bash scripts/install_ctf_tools.sh --verify
USAGE
  exit 2
fi

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

setup_logging() {
  mkdir -p "$LOG_DIR" 2>/dev/null || true
  LOG_FILE="${LOG_DIR}/install-$(date +%Y-%m-%d_%H%M%S).log"
  log_info "Logging to $LOG_FILE"
}

log_info()  { printf '\033[1;34m==>\033[0m %s\n' "$*" | tee -a "${LOG_FILE:-/dev/null}"; }
log_warn()  { printf '\033[1;33mWARNING:\033[0m %s\n' "$*" | tee -a "${LOG_FILE:-/dev/null}" >&2; }
log_error() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" | tee -a "${LOG_FILE:-/dev/null}" >&2; }
log_detail(){ printf '    %s\n' "$*" >> "${LOG_FILE:-/dev/null}"; }
# Diagnostics for functions whose stdout is captured (e.g. resolve_pip): these
# must never reach stdout, or they corrupt the captured return value.
log_verbose(){ printf '\033[1;34m==>\033[0m %s\n' "$*" >> "${LOG_FILE:-/dev/null}"; }

have() { command -v "$1" >/dev/null 2>&1; }

require_cmd() {
  if ! have "$1"; then log_error "'$1' is required but not found in PATH"; return 1; fi
}

# --------------------------------------------------------------------------- #
# Package lists
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
# Python packages — "pip_name==version:import_name"
#
# The import_name drives the skip-if-installed check, so a package that is
# already importable is not reinstalled. Pins are the versions verified by the
# upstream project (ljagiello/ctf-skills); bump deliberately, not incidentally.
#
# AI/ML packages (ctf-ai-ml) are listed WITHOUT pins on purpose: torch/transformers
# are large (multi-GB) and often unavailable for the host Python, so pinning them
# would fail the whole install. Install that direction separately when needed:
#     bash scripts/install_ctf_tools.sh python-ai
# --------------------------------------------------------------------------- #

PIP_PACKAGES=(
  "pwntools==4.15.0:pwn"
  "pycryptodome==3.23.0:Crypto"
  "z3-solver==4.13.0.0:z3"
  "sympy==1.14.0:sympy"
  "gmpy2==2.3.0:gmpy2"
  "hashpumpy==1.2:hashpumpy"
  "fpylll==0.6.4:fpylll"
  "py_ecc==8.0.0:py_ecc"
  "ecdsa==0.19.1:ecdsa"
  # angr must NOT be installed into the system python: it pulls its own z3-solver
  # into /usr/local, which shadows the apt z3 in /usr/lib and breaks the system
  # z3 install. It also needs Rust to build unless a matching wheel exists.
  # angr 9.2.193 has no cp314 manylinux x86_64 wheel, so it cannot install here;
  # 10.0.1.post1 ships cp312-abi3 manylinux_2_28_x86_64 and does.
  # Install it into its own venv instead (see the manual notes below).
  "angr==10.0.1.post1:angr"
  "frida-tools==14.8.0:frida"
  "qiling==1.4.6:qiling"
  "requests==2.32.5:requests"
  "httpx==0.27.2:httpx"
  "flask-unsign==1.2.1:flask_unsign"
  "sqlmap==1.10.3:sqlmap"
  "ropper==1.13.13:ropper"
  "ROPgadget==7.7:ropgadget"
  "volatility3==2.27.0:volatility3"
  "yara-python==4.5.4:yara"
  "pefile==2024.8.26:pefile"
  "capstone==5.0.3:capstone"
  "oletools==0.60.2:oletools"
  "unicorn==2.1.2:unicorn"
  "scapy==2.7.0:scapy"
  "Pillow==11.3.0:PIL"
  "numpy==2.2.6:numpy"
  "matplotlib==3.10.8:matplotlib"
  "shodan==1.31.0:shodan"
  "uncompyle6==3.9.3:uncompyle6"
  "lief==0.17.6:lief"
  "dnspython==2.8.0:dns"
  "dnslib==0.9.26:dnslib"
  "segno==1.6.6:segno"
  "dissect.cobaltstrike==1.2.1:dissect.cobaltstrike"
  "python-evtx==0.7.4:Evtx"
)

# Large/optional AI-ML stack (ctf-ai-ml), installed only by the 'python-ai' mode.
AI_ML_PACKAGES=(
  "torch:torch"
  "transformers:transformers"
  "safetensors:safetensors"
  "scikit-learn:sklearn"
  "scipy:scipy"
)

APT_PKGS=(
  hashcat jq curl nmap whois dnsutils
  gdb binutils strace ltrace qemu-system-x86
  radare2 apktool upx
  sagemath libgmp-dev python3-dev
  binwalk foremost libimage-exiftool-perl tshark sleuthkit
  ffmpeg steghide testdisk john pcapfix imagemagick qrencode
)

BREW_PKGS=(
  hashcat jq curl nmap whois
  gdb binutils qemu
  radare2 apktool upx
  binwalk exiftool
  ffmpeg steghide testdisk john imagemagick qrencode
)

GEM_PKGS=(
  one_gadget
  seccomp-tools
  zsteg
)

GO_PKGS=(
  github.com/ffuf/ffuf/v2@latest
)

# "TOOL|WHY|WHERE" — printed, never auto-installed.
MANUAL_ITEMS=(
  "checksec|Binary hardening checker (pwntools also ships one)|https://github.com/slimm609/checksec.sh"
  "pwndbg|GDB plugin for exploitation|https://github.com/pwndbg/pwndbg"
  "RsaCtfTool|Automated RSA attack suite|https://github.com/RsaCtfTool/RsaCtfTool"
  "SageMath|Computer algebra (apt install sagemath on Debian/Ubuntu)|https://www.sagemath.org/"
  "pycdc|Python bytecode decompiler (build from source)|https://github.com/zrax/pycdc"
  "dnSpy|.NET decompiler (Windows only)|https://github.com/dnSpy/dnSpy"
  "ysoserial|Java deserialization payload generator|https://github.com/frohoff/ysoserial"
  "r2ghidra|Native Ghidra decompiler plugin for radare2|pip install r2ghidra"
  "angr|Symbolic execution. Needs its own venv: it pins z3-solver, which would shadow the apt z3 in /usr/lib and break the system z3. 9.2.193 has no cp314 x86_64 wheel (needs Rust); use 10.x|python3 -m venv ~/.dsh/venvs/angr && ~/.dsh/venvs/angr/bin/python -m pip install angr==10.0.1.post1"
  "filebytes|ropper dependency. Its setup.py uses ast.Str/.s, removed in Python 3.12+, so the wheel build fails. Patch step.py to use ast.Constant then: python3 -m pip install --break-system-packages .|pip download --no-deps --no-binary :all: filebytes"
  "libssl-dev|Required to build hashpumpy (openssl/md4.h, openssl/sha.h)|apt-get install -y libssl-dev"
)

# --------------------------------------------------------------------------- #
# Detection helpers
# --------------------------------------------------------------------------- #

activate_venv() {
  if [ -d "$CTF_VENV/bin" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
    # shellcheck disable=SC1091
    source "$CTF_VENV/bin/activate" 2>/dev/null && log_info "Using virtualenv: $CTF_VENV"
  fi
}

py_module_installed() { python3 -c "import $1" 2>/dev/null; }
apt_pkg_installed()   { dpkg -s "$1" >/dev/null 2>&1; }
brew_pkg_installed()  { brew list --formula "$1" >/dev/null 2>&1; }
gem_installed()       { gem list -i "^${1}$" >/dev/null 2>&1; }

# Resolve the pip command, creating a venv when PEP 668 blocks the system pip.
#
# NOTE: this function's stdout is captured by the caller via command
# substitution, so it must print the pip command and NOTHING else. All
# diagnostics therefore go to log_verbose (stderr); using log_info here would
# inject its own banner into the captured value and produce a bogus command.
resolve_pip() {
  local pip_cmd=""
  for c in pip3 pip; do have "$c" && { pip_cmd="$c"; break; }; done

  local externally_managed=false
  if python3 -c "import sysconfig,os; raise SystemExit(0 if os.path.exists(os.path.join(sysconfig.get_paths()['stdlib'],'EXTERNALLY-MANAGED')) else 1)" 2>/dev/null; then
    externally_managed=true
  fi

  if [ "$externally_managed" = true ]; then
    if [ -x "$CTF_VENV/bin/pip" ]; then
      # Reference the venv's pip by absolute path: the caller may run in a
      # subshell where `source activate` cannot affect the parent's PATH.
      pip_cmd="$CTF_VENV/bin/pip"
      log_verbose "PEP 668 detected — using existing virtualenv $CTF_VENV"
    elif [ "$DRY_RUN" = true ]; then
      log_verbose "PEP 668 detected — would create virtualenv at $CTF_VENV"
    else
      log_verbose "PEP 668 detected — creating virtualenv at $CTF_VENV"
      python3 -m venv "$CTF_VENV" >>"${LOG_FILE:-/dev/null}" 2>&1 || \
        log_warn "venv creation failed — falling back to the system pip"
      if [ -x "$CTF_VENV/bin/pip" ]; then
        pip_cmd="$CTF_VENV/bin/pip"
        log_verbose "To reuse later: source $CTF_VENV/bin/activate"
      fi
    fi
  fi
  printf '%s' "$pip_cmd"
}

# --------------------------------------------------------------------------- #
# Installers
# --------------------------------------------------------------------------- #

install_python() {
  local pip_cmd; pip_cmd="$(resolve_pip)"
  if [ -z "$pip_cmd" ]; then
    log_error "no usable pip found"; FAILED+=("python: no pip"); return 1
  fi

  local -a todo=()
  for entry in "${PIP_PACKAGES[@]}"; do
    local mod="${entry##*:}" spec="${entry%%:*}"
    if [ "$FORCE" = false ] && py_module_installed "$mod"; then
      SKIPPED+=("$spec"); log_detail "skip $spec (module $mod importable)"
    else
      todo+=("$spec")
    fi
  done

  if [ "${#todo[@]}" -eq 0 ]; then
    log_info "python: all ${#PIP_PACKAGES[@]} packages already importable"
    return 0
  fi
  log_info "python: installing ${#todo[@]} packages (${#SKIPPED[@]} skipped)"
  if [ "$DRY_RUN" = true ]; then printf '    would install: %s\n' "${todo[*]}"; return 0; fi
  # Install one at a time. A single unsatisfiable pin (e.g. a version that does
  # not exist upstream) otherwise aborts the entire transaction, silently losing
  # every package in the batch — that is exactly how a bad `segno==1.6.2` pin
  # made all seven remaining packages fail.
  local ok=0 bad=()
  for pkg in "${todo[@]}"; do
    if "$pip_cmd" install "$pkg" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      ok=$((ok + 1))
    else
      bad+=("$pkg")
      log_warn "python: failed to install $pkg (continuing with the rest)"
    fi
  done
  if [ "${#bad[@]}" -eq 0 ]; then
    SUCCEEDED+=("python:${ok}")
  else
    log_error "python: ${#bad[@]} package(s) failed: ${bad[*]} — see ${LOG_FILE:-stderr}"
    FAILED+=("python:${#bad[@]}")
    return 1
  fi
}

install_python_ai() {
  local pip_cmd; pip_cmd="$(resolve_pip)"
  if [ -z "$pip_cmd" ]; then
    log_error "no usable pip found"; FAILED+=("python-ai: no pip"); return 1
  fi
  log_warn "AI/ML stack is multi-GB (torch, transformers); this can take several minutes"
  local -a todo=()
  for entry in "${AI_ML_PACKAGES[@]}"; do
    local mod="${entry##*:}" spec="${entry%%:*}"
    if [ "$FORCE" = false ] && py_module_installed "$mod"; then
      SKIPPED+=("$spec"); log_detail "skip $spec"
    else
      todo+=("$spec")
    fi
  done
  if [ "${#todo[@]}" -eq 0 ]; then log_info "python-ai: already importable"; return 0; fi
  log_info "python-ai: installing ${#todo[@]} packages"
  if [ "$DRY_RUN" = true ]; then printf '    would install: %s\n' "${todo[*]}"; return 0; fi
  if "$pip_cmd" install "${todo[@]}" >>"${LOG_FILE:-/dev/null}" 2>&1; then
    SUCCEEDED+=("python-ai:${#todo[@]}")
  else
    log_error "python-ai: install failed"; FAILED+=("python-ai"); return 1
  fi
}

install_apt() {
  require_cmd apt-get || { FAILED+=("apt: no apt-get"); return 1; }
  local -a todo=()
  for p in "${APT_PKGS[@]}"; do
    if [ "$FORCE" = false ] && apt_pkg_installed "$p"; then
      SKIPPED+=("$p"); log_detail "skip apt $p"
    else
      todo+=("$p")
    fi
  done
  if [ "${#todo[@]}" -eq 0 ]; then log_info "apt: all packages present"; return 0; fi
  log_info "apt: installing ${#todo[@]} packages (${#SKIPPED[@]} skipped)"
  if [ "$DRY_RUN" = true ]; then printf '    would install: %s\n' "${todo[*]}"; return 0; fi
  if sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q "${todo[@]}" >>"${LOG_FILE:-/dev/null}" 2>&1; then
    SUCCEEDED+=("apt:${#todo[@]}")
  else
    log_warn "apt: some packages failed (sagemath/qemu are large or may be absent); continuing"
    FAILED+=("apt(partial)")
  fi
}

install_brew() {
  require_cmd brew || { log_warn "brew not found — skipping"; return 0; }
  for p in "${BREW_PKGS[@]}"; do
    if [ "$FORCE" = false ] && brew_pkg_installed "$p"; then SKIPPED+=("$p"); continue; fi
    if [ "$DRY_RUN" = true ]; then printf '    would install: %s\n' "$p"; continue; fi
    if brew install "$p" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      SUCCEEDED+=("brew:$p")
    else
      log_warn "brew install failed: $p"; FAILED+=("brew:$p")
    fi
  done
}

install_gems() {
  require_cmd gem || { log_warn "gem not found — skipping Ruby gems"; return 0; }
  for p in "${GEM_PKGS[@]}"; do
    if [ "$FORCE" = false ] && gem_installed "$p"; then SKIPPED+=("$p"); continue; fi
    if [ "$DRY_RUN" = true ]; then printf '    would install: %s\n' "$p"; continue; fi
    if gem install "$p" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      SUCCEEDED+=("gem:$p")
    else
      log_warn "gem install failed: $p"; FAILED+=("gem:$p")
    fi
  done
}

install_go() {
  require_cmd go || { log_warn "go not found — skipping Go tools"; return 0; }
  for p in "${GO_PKGS[@]}"; do
    if [ "$DRY_RUN" = true ]; then printf '    would install: %s\n' "$p"; continue; fi
    if go install "$p" >>"${LOG_FILE:-/dev/null}" 2>&1; then
      SUCCEEDED+=("go:$p")
    else
      log_warn "go install failed: $p"; FAILED+=("go:$p")
    fi
  done
}

install_manual() {
  log_info "manual: install these yourself (not automated)"
  for item in "${MANUAL_ITEMS[@]}"; do
    local tool="${item%%|*}" rest="${item#*|}"
    local why="${rest%%|*}" where="${rest#*|}"
    printf '    %-14s %s\n      %s\n' "$tool" "$why" "$where"
  done
}

# --------------------------------------------------------------------------- #
# Verify
# --------------------------------------------------------------------------- #

verify() {
  # Do NOT activate the venv here. $CTF_VENV is created without
  # --system-site-packages, so activating it shadows the real interpreter and
  # every package installed system-wide (pwntools, pycryptodome, z3, ...) would
  # be reported missing. Verification must observe the environment the CTF
  # scripts actually run in: the system python3 (plus angr's own venv).
  local missing=() found=()

  local -a checks=(
    python3 gdb r2 objdump binwalk exiftool tshark fls ffmpeg
    testdisk john nmap whois hashcat strace ltrace convert curl jq
    apktool upx qemu-system-x86_64 qrencode ffuf gem go ROPgadget
  )

  log_info "Verifying CLI tools"
  for cmd in "${checks[@]}"; do
    if have "$cmd"; then found+=("$cmd"); else missing+=("$cmd"); fi
  done

  local -a mod_missing=() mod_found=()
  log_info "Verifying Python modules"
  for entry in "${PIP_PACKAGES[@]}"; do
    local mod="${entry##*:}" name="${entry%%:*}"
    if py_module_installed "$mod"; then mod_found+=("$name"); else mod_missing+=("$name"); fi
  done

  printf '\n  CLI found   (%2d): %s\n' "${#found[@]}" "${found[*]:-none}"
  printf '  CLI missing (%2d): %s\n' "${#missing[@]}" "${missing[*]:-none}"
  printf '\n  Py  found   (%2d): %s\n' "${#mod_found[@]}" "${mod_found[*]:-none}"
  printf '  Py  missing (%2d): %s\n' "${#mod_missing[@]}" "${mod_missing[*]:-none}"
  printf '\n'
  if [ "${#missing[@]}" -eq 0 ] && [ "${#mod_missing[@]}" -eq 0 ]; then
    log_info "verify: everything present"; return 0
  fi
  log_warn "verify: ${#missing[@]} CLI tools and ${#mod_missing[@]} Python modules missing"
  return 1
}

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

VERIFY_ONLY=false
if [ "${#MODES[@]}" -eq 1 ] && { [ "${MODES[0]}" = "--verify" ] || [ "${MODES[0]}" = "verify" ]; }; then
  VERIFY_ONLY=true
fi

if [ "$VERIFY_ONLY" = true ]; then
  verify
  exit $?
fi

setup_logging

for m in "${MODES[@]}"; do
  case "$m" in
    python)    install_python ;;
    python-ai) install_python_ai ;;
    apt)       install_apt ;;
    brew)      install_brew ;;
    gems)      install_gems ;;
    go)        install_go ;;
    manual)    install_manual ;;
    all)
      install_python
      install_apt
      install_gems
      install_go
      log_info "Skipping 'python-ai' in 'all' (multi-GB). Run it explicitly if needed."
      install_manual
      ;;
    *) echo "Unknown mode: $m" >&2; exit 2 ;;
  esac
done

# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

printf '\n'
log_info "Summary"
printf '    succeeded: %d\n' "${#SUCCEEDED[@]}"
printf '    skipped  : %d (already present)\n' "${#SKIPPED[@]}"
if [ "${#FAILED[@]}" -gt 0 ]; then
  printf '    failed   : %d -> %s\n' "${#FAILED[@]}" "${FAILED[*]}"
  printf '\n    Some installs failed. This is often benign (large or missing packages).\n'
  printf '    Re-check with: bash scripts/install_ctf_tools.sh --verify\n'
else
  printf '    failed   : 0\n'
fi
[ -n "$LOG_FILE" ] && printf '\n    log: %s\n' "$LOG_FILE"
