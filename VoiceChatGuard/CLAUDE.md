# VoiceChatGuard — WhatsApp 群组语音聊天自动退出

## 项目背景
用户的年长父亲经常在 WhatsApp 群里误触「语音聊天」功能（在聊天界面从底部输入栏上滑并按住即会开启）。WhatsApp 没有官方开关可以禁用此功能。本 app 通过 AccessibilityService 监听 WhatsApp 界面，一旦检测到父亲本人处于语音聊天中（存在「退出/Leave/End」按钮），自动点击退出。

## 目标设备
- 父亲的 Android 手机（Android 8.0+ 即可，minSdk 26）
- WhatsApp 界面语言可能是简体中文或英文，文字匹配必须两种都覆盖

## 核心需求（必须全部实现）
1. **AccessibilityService**（`VoiceChatGuardService`）：
   - 只监听 `com.whatsapp` 包（manifest 中 `android:packageNames="com.whatsapp"`）
   - 事件类型：`TYPE_WINDOW_CONTENT_CHANGED` + `TYPE_WINDOW_STATE_CHANGED`
   - 检测到语音聊天控制条中存在可点击的「退出」/「Leave」按钮时，执行 `ACTION_CLICK`
   - **关键安全规则：只在本人已加入时退出。** 判断依据：存在「退出/Leave」或挂断按钮。如果只看到「加入/Join」气泡（别人开的语音聊天），**绝对不能点击任何东西**——不理会即可。
   - 防抖：同一次点击后 3 秒内不再处理事件（用 `SystemClock.elapsedRealtime()` 记录上次动作时间）
   - 点击退出后，WhatsApp 可能弹出确认对话框（如「结束语音聊天?」/"End voice chat?"），也要检测并点击确认（「结束」/「End」/「退出」/「Leave」）
2. **MainActivity**：极简单页
   - 显示服务是否已启用（检查 `Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES`）
   - 一个大按钮跳转到无障碍设置页（`Settings.ACTION_ACCESSIBILITY_SETTINGS`）
   - 界面文字用简体中文，字体调大（老人手机可能有人帮忙设置，但保持简单）
3. **开机自启**：无障碍服务由系统自动恢复，无需 BootReceiver，但在 CLAUDE.md 的 README 部分说明需要在手机设置里把本 app 加入「不优化电池/允许后台运行」白名单（尤其小米/华为/OPPO/vivo 机型）。

## 文字匹配表（findAccessibilityNodeInfosByText，注意是包含匹配）
| 用途 | 中文 | 英文 |
|---|---|---|
| 已在语音聊天的标志 | 退出 | Leave |
| 确认对话框按钮 | 结束、退出 | End, Leave |
| 不可触碰（仅观察） | 加入 | Join |

注意：`findAccessibilityNodeInfosByText` 是子串匹配。「加入」按钮所在节点绝不点击；先检查节点树里是否有「加入/Join」且**没有**「退出/Leave」，此时直接 return。

优先尝试按 viewId 匹配（用 `adb shell uiautomator dump` 或 Layout Inspector 确认 WhatsApp 当前版本的按钮 id，例如 `com.whatsapp:id/...`），viewId 找不到再回退到文字匹配。代码里两种策略都要写，文字匹配作为兜底。

## 已有构建配置
- Gradle Kotlin DSL，AGP 8.5+，Kotlin 2.0+，无任何第三方依赖
- 项目骨架已搭好，`VoiceChatGuardService.kt` 里有核心逻辑草稿，请审查、补全并确保能编译通过
- 构建命令：`./gradlew assembleDebug`（如缺 gradle wrapper，请先 `gradle wrapper` 生成）

## 测试要点（写进 README）
1. 装到测试机 → 开启无障碍服务
2. 在任一 WhatsApp 群里自己上滑长按开启语音聊天 → 应在 1-3 秒内被自动退出
3. 让另一人开语音聊天 → 本机只显示「加入」气泡 → app 必须毫无动作
4. WhatsApp 切换为英文界面重复以上两条

## 明确不做
- 不做定时任务、不做通知栏、不做任何网络请求
- 不申请无障碍以外的敏感权限
