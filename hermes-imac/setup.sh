#!/usr/bin/env bash
#
# 在「跑 Hermes 的那台電腦」上執行，建立到 iMac 的免密碼 SSH 連線。
#
#   ./setup.sh --host imac.local --user your-mac-username
#
# 加上 --backend 會順便把 Hermes 的 terminal backend 切成 ssh
# （注意：這會讓 Hermes 的所有指令都跑在 iMac 上，詳見 README）。

set -euo pipefail

HOST=""
USER_NAME=""
PORT=22
ALIAS="imac"
KEY=""
SET_BACKEND=0

usage() {
    cat <<'EOF'
用法: ./setup.sh --host <iMac 位址> --user <iMac 使用者> [選項]

必填:
  --host <位址>     iMac 的主機名稱或 IP，例如 imac.local 或 192.168.1.23
  --user <帳號>     iMac 上的登入帳號（在 iMac 終端機執行 whoami 可查）

選項:
  --port <埠號>     SSH 埠號，預設 22
  --alias <別名>    寫進 ~/.ssh/config 的捷徑名稱，預設 imac
  --key <路徑>      私鑰路徑，預設 ~/.ssh/id_ed25519_<別名>
  --backend         同時把 Hermes 的 terminal backend 切成 ssh
  -h, --help        顯示此說明
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)    HOST="$2"; shift 2 ;;
        --user)    USER_NAME="$2"; shift 2 ;;
        --port)    PORT="$2"; shift 2 ;;
        --alias)   ALIAS="$2"; shift 2 ;;
        --key)     KEY="$2"; shift 2 ;;
        --backend) SET_BACKEND=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知參數: $1" >&2; usage >&2; exit 1 ;;
    esac
done

[[ -n "$HOST" ]] || { echo "錯誤: 缺少 --host" >&2; usage >&2; exit 1; }
[[ -n "$USER_NAME" ]] || { echo "錯誤: 缺少 --user" >&2; usage >&2; exit 1; }
[[ -n "$KEY" ]] || KEY="$HOME/.ssh/id_ed25519_${ALIAS}"

step() { echo; echo "==> $*"; }
warn() { echo "[!] $*" >&2; }

# 先確認 OpenSSH 用戶端在，否則後面的探測會把「指令不存在」誤判成「主機有回應」。
for BIN in ssh ssh-keygen; do
    command -v "$BIN" >/dev/null 2>&1 || {
        echo "錯誤: 找不到 ${BIN}，請先安裝 OpenSSH 用戶端。" >&2
        exit 1
    }
done

step "1/5 檢查 iMac 的 SSH 服務是否開著"
REACHABLE=0
if command -v nc >/dev/null 2>&1; then
    nc -z -w 5 "$HOST" "$PORT" 2>/dev/null && REACHABLE=1
else
    # Git Bash 等環境沒有 nc，改用 ssh 探測：只要不是連線層級的錯誤就算通得到。
    PROBE="$(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
                 -p "$PORT" "${USER_NAME}@${HOST}" true 2>&1 || true)"
    case "$PROBE" in
        *"Connection refused"*|*"timed out"*|*"Could not resolve"* \
        |*"No route to host"*|*"Network is unreachable"*) ;;
        *) REACHABLE=1 ;;
    esac
fi
if [[ "$REACHABLE" != "1" ]]; then
    warn "連不到 ${HOST}:${PORT}。請確認："
    warn "  - iMac 已開機且沒有睡眠"
    warn "  - iMac 的「系統設定 → 一般 → 共享 → 遠端登入」已開啟"
    warn "  - 兩台機器在同一個區網"
    exit 1
fi
echo "OK，${HOST}:${PORT} 有回應。"

step "2/5 準備 SSH 金鑰"
if [[ -f "$KEY" ]]; then
    echo "已存在，沿用 $KEY"
else
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    ssh-keygen -t ed25519 -N "" -C "hermes -> ${ALIAS}" -f "$KEY"
    echo "已產生 $KEY"
fi

step "3/5 把公鑰安裝到 iMac（這一步會問 iMac 的登入密碼）"
if ssh -o BatchMode=yes -o ConnectTimeout=5 -i "$KEY" -p "$PORT" \
       "${USER_NAME}@${HOST}" true 2>/dev/null; then
    echo "免密碼登入已經可用，略過。"
else
    PUBKEY="$(cat "${KEY}.pub")"
    # macOS 沒有內建 ssh-copy-id，所以直接用 ssh 寫入 authorized_keys。
    ssh -p "$PORT" "${USER_NAME}@${HOST}" \
        "umask 077; mkdir -p ~/.ssh; touch ~/.ssh/authorized_keys; \
         grep -qxF '$PUBKEY' ~/.ssh/authorized_keys || echo '$PUBKEY' >> ~/.ssh/authorized_keys"
    echo "公鑰已安裝。"
fi

step "4/5 寫入 ~/.ssh/config"
CONFIG="$HOME/.ssh/config"
BEGIN="# >>> hermes-imac (${ALIAS}) >>>"
END="# <<< hermes-imac (${ALIAS}) <<<"
touch "$CONFIG"
chmod 600 "$CONFIG"
if grep -qF "$BEGIN" "$CONFIG"; then
    # 移除舊區塊後重寫，讓這個腳本可以重複執行。
    awk -v b="$BEGIN" -v e="$END" '
        $0 == b {skip = 1} !skip {print} $0 == e {skip = 0}
    ' "$CONFIG" > "${CONFIG}.tmp"
    mv "${CONFIG}.tmp" "$CONFIG"
    chmod 600 "$CONFIG"
fi
cat >> "$CONFIG" <<EOF
$BEGIN
Host ${ALIAS}
    HostName ${HOST}
    User ${USER_NAME}
    Port ${PORT}
    IdentityFile ${KEY}
    IdentitiesOnly yes
    ServerAliveInterval 30
$END
EOF
echo "已加入 Host ${ALIAS}，之後可以直接用 ssh ${ALIAS}。"

step "5/5 測試連線"
ssh -o BatchMode=yes "$ALIAS" 'echo "連線成功，我是 $(whoami)@$(hostname)"'

# macOS 的隱私保護會擋掉 SSH 對「文件／桌面／下載」的存取，
# 這是設定完之後最常見的下一個問題，所以在這裡先驗一次。
if ! ssh -o BatchMode=yes "$ALIAS" 'ls ~/Documents' >/dev/null 2>&1; then
    warn "連線可以，但讀不到 ~/Documents（macOS 的完整取用權限保護）。"
    warn "請到 iMac 的「系統設定 → 隱私權與安全性 → 完整取用磁碟權限」，"
    warn "按 + 加入 /usr/libexec/sshd-keygen-wrapper，然後把「遠端登入」關掉再開啟。"
    warn "詳細步驟見 README。"
else
    echo "~/Documents 可以正常讀取。"
fi

if [[ "$SET_BACKEND" == "1" ]]; then
    step "額外: 把 Hermes 的 terminal backend 切成 ssh"
    if ! command -v hermes >/dev/null 2>&1; then
        warn "找不到 hermes 指令，跳過。請改用 hermes setup 手動設定。"
    else
        hermes config set terminal.backend ssh
        hermes config set terminal.ssh_host "$HOST"
        hermes config set terminal.ssh_user "$USER_NAME"
        hermes config set terminal.ssh_port "$PORT"
        hermes config set terminal.ssh_key "$KEY"
        echo "已設定。重啟 Hermes 後生效。"
    fi
fi

echo
echo "完成。抓檔案的方式："
echo "  ssh ${ALIAS} 'ls ~/Documents'          # 列出 iMac 上的檔案"
echo "  scp ${ALIAS}:~/Documents/foo.pdf .     # 抓單一檔案"
echo "  rsync -av ${ALIAS}:~/Documents/ ./doc/ # 同步整個資料夾"
