# qbCalculator Keyboard

让 qbCalculator 手机 app 通过 Wi-Fi 往电脑上打字、粘贴计算结果和示意图。通讯全程加密。
Type calculator results and paste diagrams from the qbCalculator app into your computer over Wi-Fi, end-to-end encrypted.

**当前版本 / Version: 2.2.0**（需要搭配支持「电脑键盘」加密协议的 qbCalculator app / requires a qbCalculator app with encrypted PC Keyboard support）

## 下载 / Download

| 系统 / System | 文件 / File |
|---|---|
| Windows 10 / 11（64 位） | [qbCalculator-Keyboard-windows-x64.exe](https://github.com/sheenhoong-wq/qbCalculator-Formulas/raw/main/pc-keyboard/qbCalculator-Keyboard-windows-x64.exe) |
| Linux（x86-64） | [qbCalculator-Keyboard-linux-x64](https://github.com/sheenhoong-wq/qbCalculator-Formulas/raw/main/pc-keyboard/qbCalculator-Keyboard-linux-x64) |
| Linux（ARM64，例如树莓派 / e.g. Raspberry Pi；只有命令行 / terminal only） | [qbCalculator-Keyboard-linux-arm64](https://github.com/sheenhoong-wq/qbCalculator-Formulas/raw/main/pc-keyboard/qbCalculator-Keyboard-linux-arm64) |

单个文件，不用安装。**请只从这个页面下载**，别的地方的同名文件可能被改过。
Single file, nothing to install. **Only download from this page.**

### 核对文件 / Verify the download

下载后可以核对 SHA-256，和 [SHA256SUMS.txt](SHA256SUMS.txt) 里的一致才是正版：
Compare the SHA-256 with [SHA256SUMS.txt](SHA256SUMS.txt):

- Windows（命令提示符 / Command Prompt）：`certutil -hashfile qbCalculator-Keyboard-windows-x64.exe SHA256`
- Linux：`sha256sum -c SHA256SUMS.txt --ignore-missing`

## 使用 / How to use

1. 运行程序 / Run it
   - **Windows**：双击运行。防火墙询问时点「允许访问」。程序暂时没有数字签名，如果提示「Windows 已保护你的电脑」，点「更多信息」→「仍要运行」。
     Double-click. Allow it through the firewall. If SmartScreen warns, click "More info" → "Run anyway".
   - **Linux**：`chmod +x qbCalculator-Keyboard-linux-x64 && ./qbCalculator-Keyboard-linux-x64`
     先安装打字工具 / install the typing tools first：`sudo apt install xdotool xclip`
     （Wayland：Sway / Hyprland 用 `wtype wl-clipboard`；GNOME / KDE 用 `ydotool wl-clipboard`）
2. 程序会打开一个窗口，显示配对二维码、电脑信息和已配对的手机。/ A window opens with the pairing QR code, computer info and paired phones.
3. 手机和电脑连同一个 Wi-Fi。在 app 里打开侧边菜单 →「电脑键盘」→「扫码配对」，扫窗口里的二维码。
   Put the phone and the computer on the same Wi-Fi. In the app: menu → PC Keyboard → Scan QR code, and scan the QR code in the window.
   没有相机：用「验证码配对」，电脑会弹出确认窗口，两边验证码一样才点「一样，允许」。
   No camera: use "Pair with verification code"; the computer shows a confirmation dialog — click "Yes, allow" only if both codes match.
4. 配对一次就记住了。把电脑上的光标放到要输入的地方，在手机上操作即可。
   Pairing is remembered. Put the cursor where the text should go and use the phone.

窗口里的操作 / In the window：

- **生成新的二维码 / New QR code**：二维码 10 分钟有效、只能配对一部手机，过期或用过后点这个。/ QR codes are valid for 10 minutes and pair one phone.
- **撤销 / Revoke**：在已配对手机列表里点「撤销」再点「确定撤销？」。手机丢了就用这个。/ Click "Revoke" then "Confirm?" in the paired phones list, e.g. if a phone is lost.
- **开机自动运行 / Start at login**：勾选后登录电脑就自动打开（最小化，不需要管理员权限）。移动了程序文件的话要重新勾选。/ Tick it to start minimized after logging in (no administrator rights needed). Tick it again if you move the program file.

界面语言跟随系统（中文或英文）。/ The window follows the system language (Chinese or English).
命令行模式 / Terminal mode：加 `-console` 运行（Linux ARM64 版和没有桌面时自动使用），二维码印在终端里，命令：回车 = 新二维码 · `list` · `revoke 编号` · `autostart on|off`。
Run with `-console` (always used on Linux ARM64 or without a desktop): Enter = new QR code · `list` · `revoke N` · `autostart on|off`.

## 模式 / Modes

点计算器顶栏的电脑按钮选择 / Tap the computer button at the top of the calculator:

- **关闭 / Off**：不发送 / nothing is sent
- **即时输入 / Instant input**：计算器上按什么，电脑上马上打什么；按 `=` 换行 / keys you tap are typed right away; `=` presses Enter
- **复制粘贴 / Copy & paste**：长按 `=` 发送答案；长按算式、历史记录或示意图，选「发到电脑」/ long-press `=` to send the answer; long-press the expression, a history entry or a diagram and choose "To PC"

## 安全 / Security

- 通讯全程加密（ECDH P-256 + AES-256-GCM），每次连接使用新的会话密钥；被篡改或重放的数据会被拒绝。
  End-to-end encrypted with fresh session keys; tampered or replayed data is rejected.
- 手机和电脑互相认证：二维码 10 分钟有效、只能用一次；每部手机有自己的密钥，可以随时撤销。
  Mutual authentication: single-use QR codes valid for 10 minutes; per-phone keys you can revoke.
- 手机只能打字、粘贴，和按回车 / Tab / 方向键 / 退格等少数几个键，不能按组合键，不能运行程序或读取文件。
  The phone can only type, paste and press a few keys (Enter, Tab, arrows, Backspace) — no shortcuts, no running programs, no file access.
- 关闭程序窗口就停止工作（最小化时仍在工作）。/ Closing the window stops it (it keeps working while minimized).

## 常见问题 / FAQ

- **搜索不到 / Not found**：扫码配对不需要搜索。有些路由器（访客网络、公司网络）不允许设备互相连接。/ QR pairing needs no search; some guest or office networks block devices from reaching each other.
- **连不上 / Cannot connect**：检查防火墙；Linux 用 ufw 时：`sudo ufw allow 47821/tcp` 和 `sudo ufw allow 47820/udp`。
- **以管理员身份运行的窗口打不进字（Windows）**：qbCalculator Keyboard 也要以管理员身份运行。/ Windows running as administrator need qbCalculator Keyboard to run as administrator too.
- **支持多国语言 / Any language**：中文、日文、韩文、阿拉伯文、俄文等都可以，不用切换输入法。/ Works with any language without switching input methods.

## 版本记录 / Changelog

- **2.2.0**：新的窗口界面：二维码、已配对手机、撤销、开机自启都可以直接点。/ New window UI: QR code, paired phones, revoke and start at login with buttons.
- **2.1.2**：可以设置开机自启（`autostart on`）。/ Optional start at login (`autostart on`).
- **2.1.1**：小幅改进。/ Minor improvements.
- **2.1.0**：改名为 qbCalculator Keyboard。
  Renamed to qbCalculator Keyboard.
- **2.0.0**：全程加密、扫码 / 验证码配对、撤销手机、粘贴示意图、Windows 和 Linux 都用剪贴板粘贴非英文文字。
  End-to-end encryption, QR / code pairing, revoking phones, pasting diagrams, clipboard paste for non-English text.
