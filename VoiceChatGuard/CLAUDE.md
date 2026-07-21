# VoiceChatGuard — WhatsApp 群组语音聊天自动退出

## 项目背景
用户的年长父亲经常在 WhatsApp 群里误触「语音聊天」功能（在聊天界面从底部输入栏上滑并按住即会开启）。WhatsApp 没有官方开关可以禁用此功能。本 app 通过 AccessibilityService 监听 WhatsApp 界面，一旦检测到父亲本人误开了群组语音聊天，自动点击退出，并发通知告知（通知带「暂停30分钟/1小时」按钮）。

## 目标设备
- 父亲的 Android 手机（minSdk 26）
- WhatsApp 界面语言可能是简体中文或英文，文字匹配必须两种都覆盖

## 拦截范围（最重要的需求，必须严格遵守）
| 场景 | 处理 |
|---|---|
| 本人误开的**群组语音聊天**（Voice chat，上滑长按触发的那种） | ✅ 自动退出 + 发通知 |
| 一对一语音/视频**通话**（主动拨出） | ❌ 绝不干预 |
| 别人**打来的来电**（接听界面） | ❌ 绝不干预 |
| 正常的**群组通话**（Group call，从通话按钮发起的） | ❌ 绝不干预 |
| **别人开启**的语音聊天（本机只显示「加入/Join」气泡） | ❌ 绝不干预 |
| 暂停期内（用户点了通知上的暂停按钮） | ❌ 不干预 |

区分「语音聊天」和「通话」的判定策略（三层防线，代码已写好草稿）：
1. `event.className` 含 voip/call 关键词 → 直接忽略（通话界面 Activity 名与会话界面不同，请用 `adb shell dumpsys activity top` 实测确认 WhatsApp 当前版本的通话 Activity 类名，写死进 `CALL_ACTIVITY_HINTS`）
2. 节点树出现任何通话/来电特征文字（来电/接听/拒绝/挂断/Calling/Ringing 等）→ 忽略
3. 必须同时满足：节点树含「语音聊天/Voice chat」标记 **且** 含「退出/Leave」按钮，才执行退出。只满足其一都不动作（宁可漏拦，不可错拦）

## 通知与暂停功能
- 拦截成功后发通知：「已自动退出语音聊天」，带两个 action 按钮「暂停30分钟」「暂停1小时」
- 按钮通过 `SnoozeReceiver` 写入 SharedPreferences 的 `snooze_until_epoch_ms`
- Service 每次处理事件前先检查是否在暂停期内
- Android 13+ 需要 POST_NOTIFICATIONS 运行时权限，MainActivity 已请求
- 已实现草稿：`VoiceChatGuardService.kt` + `SnoozeReceiver.kt`，请审查补全

## 文字匹配表（findAccessibilityNodeInfosByText 为子串匹配）
| 用途 | 中文 | 英文 |
|---|---|---|
| 语音聊天标记（必须存在才动作） | 语音聊天 | Voice chat |
| 退出按钮 | 退出 | Leave |
| 确认对话框按钮 | 结束、退出 | End, Leave |
| 通话/来电特征（出现即忽略） | 来电、接听、拒绝、挂断、视频通话 | Incoming, Answer, Decline, Ringing, Calling |
| 仅观察绝不点击 | 加入 | Join |

优先用 viewId 匹配（`LEAVE_VIEW_IDS` 目前为空，请用 `adb shell uiautomator dump` 实测语音聊天控制条的退出按钮 id 填入；注意与通话界面挂断按钮 id 区分开），文字匹配作兜底。

## 其他要求
- 防抖 3 秒；退出后的确认对话框也要点掉（不重复发通知）
- MainActivity 极简：显示服务状态 + 跳无障碍设置按钮，中文大字
- 无任何网络请求、不收集数据、除通知外不申请其他敏感权限
- 构建：`./gradlew assembleDebug`（缺 wrapper 先 `gradle wrapper`）

## 测试清单（写进 README）
1. 自己在群里上滑长按开语音聊天 → 1-3 秒自动退出 + 收到通知
2. 点通知「暂停30分钟」→ 再开语音聊天 → 不被退出
3. 别人开语音聊天（本机只有加入气泡）→ 无任何动作
4. 一对一打电话给别人 → 通话全程不被挂断
5. 别人打来电话 → 响铃和接听后都不被挂断
6. 群组通话（从通话按钮发起）→ 不被挂断
7. WhatsApp 切英文界面重复 1、3、4、5
