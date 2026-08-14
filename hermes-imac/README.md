# 讓 Hermes 連到 iMac 抓檔案

把 [Hermes Agent](https://github.com/NousResearch/hermes-agent) 接到同一個區網裡的 iMac，
讓它可以列出、讀取、下載 iMac 上的檔案。走的是 macOS 內建的 SSH（遠端登入），
不需要在 iMac 上安裝任何東西。

- **iMac** = 檔案放的地方（被連的那一台）
- **Hermes 機器** = Hermes 裝在上面、發起連線的那一台

---

## 步驟一：在 iMac 上開啟遠端登入

在 **iMac** 上操作：

1. 「系統設定」→「一般」→「共享」
2. 打開 **「遠端登入」**
3. 點旁邊的 ⓘ，確認「允許存取」包含你的帳號

順手記下兩個等一下會用到的值，在 iMac 的「終端機」執行：

```bash
whoami                  # 你的帳號名稱，例如 dextra
scutil --get LocalHostName   # 主機名稱，例如 iMac → 連線時用 iMac.local
```

如果 `.local` 名稱不穩，改用 IP：「系統設定」→「網路」→ Wi-Fi/乙太網路 →「詳細資訊」→「TCP/IP」。

## 步驟二：開放 SSH 讀取「文件／桌面／下載」

**這一步不做的話，連得上但會讀不到檔案**，`ls ~/Documents` 會回 `Operation not permitted`。
macOS 的隱私保護預設會擋住 SSH 對這幾個資料夾的存取。

在 **iMac** 上：

1. 「系統設定」→「隱私權與安全性」→「完整取用磁碟權限」
2. 按 **+**，用 `Cmd + Shift + G` 貼上路徑 `/usr/libexec/sshd-keygen-wrapper`，加入並開啟開關
3. 回到「共享」把 **「遠端登入」關掉再重新開啟**（讓 sshd 重啟套用權限）

如果只需要抓某個特定資料夾（例如 `~/Projects`）而不碰文件／桌面／下載，這一步可以略過。

## 步驟三：在 Hermes 機器上跑設定腳本

```bash
cd hermes-imac
chmod +x setup.sh
./setup.sh --host iMac.local --user 你的iMac帳號
```

腳本會依序：確認 iMac 的 SSH 有回應 → 產生專用金鑰 → 把公鑰裝到 iMac（**會問一次 iMac 的登入密碼**）
→ 寫進 `~/.ssh/config` → 測試連線 → 順便檢查上面那個權限坑。

跑完之後 `ssh imac` 就能免密碼直接進 iMac。腳本可以重複執行，不會重複寫設定。

> **Windows 上的 Hermes**：`setup.sh` 需要 bash，請在 Git Bash 或 WSL 裡跑。
> Windows 10/11 內建的 OpenSSH 客戶端指令完全相同。

---

## 兩種用法，擇一

### 用法 A：Hermes 留在本機，需要時才去 iMac 抓（建議）

不用改任何 Hermes 設定。做完上面三步之後，直接叫 Hermes 用終端機工具跑：

```bash
ssh imac 'ls -la ~/Documents'            # 看 iMac 上有什麼
scp imac:~/Documents/報價單.pdf .         # 抓單一檔案回本機
rsync -av imac:~/Projects/ ./projects/   # 同步整個資料夾回本機
```

Hermes 的其他能力照舊在本機運作，只有抓檔案這件事會走到 iMac。
日常「去 iMac 拿個東西」用這個就夠了。

### 用法 B：把 Hermes 整個工作環境搬到 iMac

Hermes 內建 SSH terminal backend，切過去之後**所有**指令都在 iMac 上執行，
等於 Hermes 直接住在 iMac 裡工作。

```bash
./setup.sh --host iMac.local --user 你的iMac帳號 --backend
```

或用 Hermes 自己的互動式設定：`hermes setup`，terminal backend 選 `ssh`。

手動設定的話，`~/.hermes/config.yaml`：

```yaml
terminal:
  backend: ssh
  persistent_shell: true
  ssh_host: "iMac.local"
  ssh_user: "你的iMac帳號"
  ssh_port: 22
  ssh_key: "~/.ssh/id_ed25519_imac"
```

改完要重啟 Hermes。

**選這個之前先想清楚**：切成 ssh backend 後，Hermes 就碰不到本機的檔案了。
如果 iMac 睡著或斷網，Hermes 的終端機工具會整個失效。只是要抓檔案的話請選用法 A。

---

## 疑難排解

| 症狀 | 原因與處理 |
|---|---|
| `Connection refused` | iMac 的「遠端登入」沒開 |
| 連不到 `iMac.local` | 改用 IP；或確認兩台在同一個區網、沒被訪客網路隔離 |
| `Permission denied (publickey)` | 公鑰沒裝成功。刪掉 `~/.ssh/id_ed25519_imac*` 重跑 `setup.sh` |
| `ls: Operation not permitted` | 步驟二沒做，或做完沒把「遠端登入」關掉再開 |
| 過一陣子就斷線 | iMac 睡著了。「系統設定」→「鎖定畫面」把「顯示器關閉時自動進入睡眠」設為「永不」 |
| Hermes 切了 ssh backend 後起不來 | `hermes config set terminal.backend local` 切回來 |

## 安全性

- 金鑰是 `~/.ssh/id_ed25519_imac` 這把專用的，跟你其他 SSH 金鑰分開，之後要撤銷只要從 iMac 的 `~/.ssh/authorized_keys` 移掉那一行。
- **只在信任的區網做這件事。** 不要為了遠端存取把 iMac 的 22 埠對外開放到 public internet，要跨網路請用 Tailscale 或 WireGuard。
- Hermes 拿到的權限等同於你這個 macOS 帳號，它讀得到你讀得到的所有東西。真的要限制範圍的話，在 iMac 上開一個只有必要資料夾權限的專用帳號來連。
