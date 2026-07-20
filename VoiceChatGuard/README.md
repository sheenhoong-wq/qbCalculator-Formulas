# VoiceChatGuard 语音聊天守卫

自动退出 WhatsApp 群组中误开的语音聊天。给不熟悉手机操作的长辈使用。

## 构建

本地构建（需要 Android SDK 和网络）：

```bash
./gradlew assembleDebug
# 输出：app/build/outputs/apk/debug/app-debug.apk
```

也可以用仓库自带的 GitHub Actions 工作流（`.github/workflows/build-voicechatguard.yml`）：
推送本目录的改动或手动触发 workflow，构建完成后 APK 会作为 artifact 上传，
并以 `VoiceChatGuard/app-debug.apk` 提交回分支。

## 安装步骤（爸爸的手机）
1. 安装 `app-debug.apk`（安装时如提示「未知来源」，允许即可）
2. 打开「语音聊天守卫」→ 点「打开无障碍设置」→ 开启本服务
3. 手机设置 → 电池 → 把本 app 设为「不限制/不优化」（小米/华为/OPPO/vivo 必须做这一步，否则服务会被杀）

## 工作原理与安全规则
- 无障碍服务只监听 `com.whatsapp` 的窗口事件，不做任何网络请求，不收集数据
- 只有检测到「退出/Leave」类按钮（代表本人已在语音聊天中）才会点击退出；
  只看到「加入/Join」气泡（别人开的语音聊天）时绝不动作
- 文字匹配要求整字匹配或同时含「语音聊天」字样，避免误点「退出群组」等其他按钮
- 点击退出后若弹出确认对话框（「结束语音聊天?」/"End voice chat?"），会自动点击确认
- 优先按 viewId 匹配按钮，文字匹配作为兜底；WhatsApp 改版后若 viewId 变化，
  可用 `adb shell uiautomator dump` 确认实际 id 并补充到 `VoiceChatGuardService.kt`

## 测试清单
- [ ] 自己在群里上滑长按开启语音聊天 → 1-3 秒内自动退出
- [ ] 别人开语音聊天时，本机只有「加入」气泡 → app 无任何动作
- [ ] WhatsApp 切英文界面，重复以上两条
- [ ] 打开群组信息页（有「退出群组」按钮）→ app 无任何动作
