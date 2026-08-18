#!/usr/bin/env bash
#
# 走 Tailscale 連 iMac：自動從 tailscale status 找出目標機器，再交給 setup.sh。
#
#   ./setup-tailscale.sh --user your-mac-username
#
# 預設用 Tailscale 的 100.x.y.z 位址，因為 MagicDNS 在 macOS 上偶爾解析不到。
# 想用 MagicDNS 名稱請加 --magicdns。

set -euo pipefail

USER_NAME=""
NAME_FILTER=""
ALIAS="imac"
USE_MAGICDNS=0
PASSTHRU=()

usage() {
    cat <<'EOF'
用法: ./setup-tailscale.sh --user <iMac 使用者> [選項]

必填:
  --user <帳號>     iMac 上的登入帳號（在 iMac 終端機執行 whoami 可查）

選項:
  --name <關鍵字>   直接指定 tailnet 上的機器名稱，跳過選單
  --alias <別名>    寫進 ~/.ssh/config 的捷徑名稱，預設 imac
  --magicdns        用 MagicDNS 名稱而非 100.x.y.z 位址
  --backend         同時把 Hermes 的 terminal backend 切成 ssh
  -h, --help        顯示此說明
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)     USER_NAME="$2"; shift 2 ;;
        --name)     NAME_FILTER="$2"; shift 2 ;;
        --alias)    ALIAS="$2"; shift 2 ;;
        --magicdns) USE_MAGICDNS=1; shift ;;
        --backend)  PASSTHRU+=("--backend"); shift ;;
        -h|--help)  usage; exit 0 ;;
        *) echo "未知參數: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[[ -n "$USER_NAME" ]] || { echo "錯誤: 缺少 --user" >&2; usage >&2; exit 1; }

warn() { echo "[!] $*" >&2; }

# --- 找 tailscale CLI --------------------------------------------------------
# macOS 的 GUI 版（App Store / standalone）不會把 CLI 放進 PATH，
# 二進位檔藏在 app bundle 裡。
TS=""
for CANDIDATE in \
    tailscale \
    /Applications/Tailscale.app/Contents/MacOS/Tailscale \
    /opt/homebrew/bin/tailscale \
    /usr/local/bin/tailscale
do
    if command -v "$CANDIDATE" >/dev/null 2>&1; then TS="$CANDIDATE"; break; fi
done
if [[ -z "$TS" ]]; then
    warn "找不到 tailscale 指令。若已安裝 GUI 版，可以先設 alias："
    warn "  alias tailscale=\"/Applications/Tailscale.app/Contents/MacOS/Tailscale\""
    exit 1
fi

command -v python3 >/dev/null 2>&1 || {
    warn "找不到 python3，無法解析 tailscale status --json。"
    warn "改用 ./setup.sh --host <100.x.y.z> --user ${USER_NAME} 手動指定。"
    exit 1
}

# --- 列出 tailnet 上的機器 ---------------------------------------------------
echo "==> 讀取 tailscale status"
TS_ERR="$(mktemp)"
trap 'rm -f "$TS_ERR"' EXIT
set +e
PEERS="$("$TS" status --json 2>/dev/null | python3 -c '
import json, sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.stderr.write("PARSE_FAILED\n")
    sys.exit(4)

state = data.get("BackendState", "")
if state != "Running":
    sys.stderr.write("STATE=%s\n" % (state or "unknown"))
    sys.exit(3)

for peer in (data.get("Peer") or {}).values():
    ips = peer.get("TailscaleIPs") or []
    v4 = next((ip for ip in ips if ":" not in ip), "")
    if not v4:
        continue
    print("\t".join([
        peer.get("HostName") or "",
        (peer.get("DNSName") or "").rstrip("."),
        v4,
        peer.get("OS") or "",
        "online" if peer.get("Online") else "offline",
    ]))
' 2>"$TS_ERR")"
RC=$?
set -e

if [[ $RC -eq 3 ]]; then
    TS_STATE="$(sed -n 's/^STATE=//p' "$TS_ERR" | head -1)"
    warn "Tailscale 目前不是運作中的狀態（${TS_STATE:-unknown}）。"
    warn "請先開啟 Tailscale 並登入，然後再跑一次。"
    exit 1
elif [[ $RC -ne 0 ]]; then
    warn "讀取 tailscale status 失敗。"
    exit 1
fi
# 底下用 exec 交棒，EXIT trap 不會執行，所以在這裡就把暫存檔收掉。
rm -f "$TS_ERR"

if [[ -n "$NAME_FILTER" ]]; then
    PEERS="$(printf '%s\n' "$PEERS" | grep -i -- "$NAME_FILTER" || true)"
fi
PEERS="$(printf '%s\n' "$PEERS" | grep -v '^[[:space:]]*$' || true)"

if [[ -z "$PEERS" ]]; then
    if [[ -n "$NAME_FILTER" ]]; then
        warn "tailnet 上找不到符合「${NAME_FILTER}」的機器。"
    else
        warn "tailnet 上除了本機之外沒有其他機器。請確認 iMac 也已安裝 Tailscale 並登入同一個 tailnet。"
    fi
    exit 1
fi

# --- 選一台 ------------------------------------------------------------------
COUNT="$(printf '%s\n' "$PEERS" | wc -l | tr -d ' ')"
if [[ "$COUNT" == "1" ]]; then
    CHOICE="$PEERS"
    echo "找到唯一符合的機器："
    printf '%s\n' "$CHOICE" | awk -F'\t' '{printf "  %s (%s, %s, %s)\n", $1, $3, $4, $5}'
else
    echo "tailnet 上的機器："
    printf '%s\n' "$PEERS" | awk -F'\t' '{printf "  [%d] %-20s %-16s %-8s %s\n", NR, $1, $3, $4, $5}'
    printf '選擇要連的機器編號: '
    read -r PICK
    [[ "$PICK" =~ ^[0-9]+$ ]] || { warn "請輸入數字。"; exit 1; }
    CHOICE="$(printf '%s\n' "$PEERS" | sed -n "${PICK}p")"
    [[ -n "$CHOICE" ]] || { warn "沒有編號 ${PICK} 這台。"; exit 1; }
fi

HOSTNAME_SHORT="$(printf '%s' "$CHOICE" | cut -f1)"
DNS_NAME="$(printf '%s' "$CHOICE" | cut -f2)"
TS_IP="$(printf '%s' "$CHOICE" | cut -f3)"
PEER_OS="$(printf '%s' "$CHOICE" | cut -f4)"
PEER_ONLINE="$(printf '%s' "$CHOICE" | cut -f5)"

if [[ "$PEER_ONLINE" != "online" ]]; then
    warn "${HOSTNAME_SHORT} 目前顯示離線，iMac 可能睡著或關機了。還是會試著連連看。"
fi
if [[ -n "$PEER_OS" && "$PEER_OS" != "macOS" ]]; then
    warn "${HOSTNAME_SHORT} 的系統是 ${PEER_OS}，不是 macOS。確定是這一台嗎？"
fi

if [[ "$USE_MAGICDNS" == "1" && -n "$DNS_NAME" ]]; then
    TARGET="$DNS_NAME"
else
    TARGET="$TS_IP"
fi

echo
echo "==> 目標: ${HOSTNAME_SHORT} → ${TARGET}"
echo

# --- 交給主腳本 --------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# bash 3.2（macOS 內建）在 set -u 下展開空陣列會報錯，要用這個寫法。
exec "${SCRIPT_DIR}/setup.sh" \
    --host "$TARGET" \
    --user "$USER_NAME" \
    --alias "$ALIAS" \
    ${PASSTHRU[@]+"${PASSTHRU[@]}"}
