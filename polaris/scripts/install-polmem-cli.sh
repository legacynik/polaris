#!/usr/bin/env bash
# polaris/scripts/install-polmem-cli.sh
# Make `polmem` available on your shell PATH.
#
# Installs a tiny launcher at ~/.local/bin/polmem that, at RUN TIME, resolves the
# newest installed polaris-team-os plugin-cache shim and execs it. The launcher is
# version-independent: it never pins a plugin version, so `claude plugin update`
# does not break it. Idempotent and re-runnable.
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/polmem"

mkdir -p "${BIN_DIR}"

cat > "${LAUNCHER}" <<'LAUNCHER_EOF'
#!/usr/bin/env bash
# polmem launcher (installed by polaris-team-os install-polmem-cli.sh).
# Resolves the newest installed polaris-team-os plugin shim at run time — never a
# pinned version — so plugin updates keep working with no reinstall.
set -euo pipefail
CACHE="${HOME}/.claude/plugins/cache"
# Highest-version bin/polmem under any polaris-team-os plugin cache dir.
SHIM="$(find "${CACHE}" -type f -path '*polaris-team-os*/bin/polmem' 2>/dev/null | sort -V | tail -n1)"
if [ -z "${SHIM:-}" ]; then
  echo "polmem: polaris-team-os plugin not installed (no shim under ${CACHE})." >&2
  echo "  Install it in Claude Code:  /plugin install polaris-team-os@polaris-team-os" >&2
  exit 127
fi
exec python3 "${SHIM}" "$@"
LAUNCHER_EOF

chmod +x "${LAUNCHER}"

echo "installed: ${LAUNCHER}"
case ":${PATH}:" in
  *":${BIN_DIR}:"*) echo "PATH: ${BIN_DIR} already on PATH — run: polmem health" ;;
  *) echo "PATH: ${BIN_DIR} is NOT on your PATH. Add this to your shell profile:"
     echo "  export PATH=\"\${HOME}/.local/bin:\${PATH}\"" ;;
esac
