# qbCalculator 电脑键盘 / PC Keyboard

让 qbCalculator 手机 app 通过 Wi-Fi 往电脑上打字、粘贴计算结果和示意图。通讯全程加密。
Type calculator results and paste diagrams from the qbCalculator app into your computer over Wi-Fi, end-to-end encrypted.

**当前版本 / Version: 2.0.0**（需要搭配支持「电脑键盘」加密协议的 qbCalculator app / requires a qbCalculator app with encrypted PC Keyboard support）

## 下载 / Download

| 系统 / System | 文件 / File |
|---|---|
| Windows 10 / 11（64 位） | [qbkeyboard-windows-x64.exe](https://github.com/sheenhoong-wq/qbCalculator-Formulas/raw/main/pc-keyboard/qbkeyboard-windows-x64.exe) |
| Linux（x86-64） | [qbkeyboard-linux-x64](https://github.com/sheenhoong-wq/qbCalculator-Formulas/raw/main/pc-keyboard/qbkeyboard-linux-x64) |
| Linux（ARM64，例如树莓派 / e.g. Raspberry Pi） | [qbkeyboard-linux-arm64](https://github.com/sheenhoong-wq/qbCalculator-Formulas/raw/main/pc-keyboard/qbkeyboard-linux-arm64) |

单个文件，不用安装。**请只从这个页面下载**，别的地方的同名文件可能被改过。
Single file, nothing to install. **Only download from this page.**

### 核对文件 / Verify the download

下载后可以核对 SHA-256，和 [SHA256SUMS.txt](SHA256SUMS.txt) 里的一致才是正版：
Compare the SHA-256 with [SHA256SUMS.txt](SHA256SUMS.txt):

- Windows（命令提示符 / Command Prompt）：`certutil -hashfile qbkeyboard-windows-x64.exe SHA256`
- Linux：`sha256sum -c SHA256SUMS.txt --ignore-missing`

## 使用 / How to use

1. 运行程序 / Run it
   - **Windows**：双击运行。防火墙询问时点「允许访问」。程序暂时没有数字签名，如果提示「Windows 已保护你的电脑」，点「更多信息」→「仍要运行」。
     Double-click. Allow it through the firewall. If SmartScreen warns, click "More info" → "Run anyway".
   - **Linux**：`chmod +x qbkeyboard-linux-x64 && ./qbkeyboard-linux-x64`
     先安装打字工具 / install the typing tools first：`sudo apt install xdotool xclip`
     （Wayland：Sway / Hyprland 用 `wtype wl-clipboard`；GNOME / KDE 用 `ydotool wl-clipboard`）
2. 手机和电脑连同一个 Wi-Fi。/ Put the phone and the computer on the same Wi-Fi.
3. 在 app 里打开侧边菜单 →「电脑键盘」→「扫码配对」，扫程序窗口里的二维码。
   In the app: menu → PC Keyboard → Scan QR code, and scan the QR code in the program window.
   没有相机：用「验证码配对」，两边验证码一样才在电脑窗口输入 `y` 回车。
   No camera: use "Pair with verification code" and type `y` in the window only if both codes match.
4. 配对一次就记住了。把电脑上的光标放到要输入的地方，在手机上操作即可。
   Pairing is remembered. Put the cursor where the text should go and use the phone.

窗口里的命令 / Commands in the window：回车 Enter = 新二维码 new QR code · `list` = 已配对的手机 paired phones · `revoke 编号` = 撤销 revoke（`revoke all` 全部 / all）

## 三种模式 / Modes

- **即时键盘 / Instant keyboard**：手机上按一下，电脑上打一下 / each key is typed right away
- **发送结果 / Send result**：每次按 `=` 把结果打到电脑上 / the result is typed after every `=`
- **发送算式和结果 / Send expression and result**：例如 / e.g. `12×3 = 36`
- 示意图和开板图：点「发到电脑」直接粘贴 / Diagrams and cut sheets: tap "To PC" to paste them

## 安全 / Security

- 通讯全程加密（ECDH P-256 + AES-256-GCM），每次连接使用新的会话密钥；被篡改或重放的数据会被拒绝。
  End-to-end encrypted with fresh session keys; tampered or replayed data is rejected.
- 手机和电脑互相认证：二维码 10 分钟有效、只能用一次；每部手机有自己的密钥，可以随时撤销。
  Mutual authentication: single-use QR codes valid for 10 minutes; per-phone keys you can revoke.
- 手机只能打字、粘贴，和按回车 / Tab / 方向键 / 退格等少数几个键，不能按组合键，不能运行程序或读取文件。
  The phone can only type, paste and press a few keys (Enter, Tab, arrows, Backspace) — no shortcuts, no running programs, no file access.
- 关闭程序窗口就停止工作。/ Closing the window stops it.

## 常见问题 / FAQ

- **搜索不到 / Not found**：扫码配对不需要搜索。有些路由器（访客网络、公司网络）不允许设备互相连接。/ QR pairing needs no search; some guest or office networks block devices from reaching each other.
- **连不上 / Cannot connect**：检查防火墙；Linux 用 ufw 时：`sudo ufw allow 47821/tcp` 和 `sudo ufw allow 47820/udp`。
- **以管理员身份运行的窗口打不进字（Windows）**：qbkeyboard 也要以管理员身份运行。/ Windows running as administrator need qbkeyboard to run as administrator too.
- **支持多国语言 / Any language**：中文、日文、韩文、阿拉伯文、俄文等都可以，不用切换输入法。/ Works with any language without switching input methods.

## 版本记录 / Changelog

- **2.0.0**：全程加密、扫码 / 验证码配对、撤销手机、粘贴示意图、Windows 和 Linux 都用剪贴板粘贴非英文文字。
  End-to-end encryption, QR / code pairing, revoking phones, pasting diagrams, clipboard paste for non-English text.
