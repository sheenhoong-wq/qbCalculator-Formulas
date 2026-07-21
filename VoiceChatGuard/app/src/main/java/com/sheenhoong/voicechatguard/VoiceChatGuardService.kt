package com.sheenhoong.voicechatguard

import android.accessibilityservice.AccessibilityService
import android.content.Context
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * 监听 WhatsApp 界面，检测到本人误开「群组语音聊天」时自动点击「退出」，
 * 并发通知提醒（带「暂停30分钟/1小时」按钮）。
 *
 * 拦截范围（严格限定，宁可漏拦，不可错拦）：
 *  - 只拦截：群聊里的「语音聊天」（Voice chat，上滑长按误触开启的那种）
 *  - 不拦截：一对一语音/视频通话、别人打来的来电、正常的群组通话
 *    （通话界面没有「语音聊天/Voice chat」字样，且有三层防线：
 *     通话 Activity 类名 → 通话/来电特征文字 → 必须同时存在语音聊天标记和退出按钮）
 *  - 不拦截：别人开启的语音聊天（只显示「加入/Join」气泡时绝不动作）
 *  - 不拦截：暂停期内（用户点了通知上的暂停按钮）
 */
class VoiceChatGuardService : AccessibilityService() {

    companion object {
        private const val TAG = "VoiceChatGuard"
        private const val WHATSAPP_PACKAGE = "com.whatsapp"

        const val CHANNEL_ID = "guard_events"
        const val PREFS = "guard_prefs"
        const val KEY_SNOOZE_UNTIL = "snooze_until_epoch_ms"
        const val NOTIFICATION_ID = 1001

        /** 点击「退出」后 3 秒内不再触发新的退出动作（防抖） */
        private const val LEAVE_DEBOUNCE_MS = 3000L

        /** 点击「退出」后，在此时间窗口内寻找并点击确认对话框 */
        private const val CONFIRM_WINDOW_MS = 8000L

        /** 两次确认按钮点击之间的最小间隔 */
        private const val CONFIRM_DEBOUNCE_MS = 800L

        /** 节点本身不可点击时，最多向上找几层父节点 */
        private const val MAX_ANCESTOR_DEPTH = 3

        // ---- 语音聊天（要拦截的）特征文字，包含匹配、不区分大小写 ----
        // 必须存在这些标记才可能动作；一对一/群组「通话」界面显示的是
        // 「语音通话/Voice call」，不会命中「语音聊天/Voice chat」
        private val VOICE_CHAT_WORDS = listOf("语音聊天", "voice chat")

        // 「退出」类关键词，用于 findAccessibilityNodeInfosByText 初筛（子串匹配）
        private val LEAVE_WORDS = listOf("退出", "离开", "leave")

        // 完整等于这些文字的节点才视为退出按钮（防止误点「退出群组」「退出登录」等）
        private val LEAVE_EXACT = listOf("退出", "离开", "leave")

        // 确认对话框按钮的完整文字（点击退出后 WhatsApp 可能再确认一次）
        private val CONFIRM_EXACT = listOf(
            "结束", "退出", "离开", "end", "leave",
            "结束语音聊天", "退出语音聊天", "end voice chat", "leave voice chat"
        )

        // 文字含这些词的节点绝不点击（别人开的语音聊天只有「加入」气泡）
        private val JOIN_WORDS = listOf("加入", "join")

        // 通话/来电界面的特征文字：屏幕上出现任何一个，本次事件直接忽略。
        // 注意不能用「语音通话/voice call」——聊天记录里的「未接语音通话」
        // 条目会包含它，导致有通话记录的群聊永远不被保护。
        private val CALL_SCREEN_MARKERS = listOf(
            "来电", "接听", "拒绝", "挂断", "响铃", "正在呼叫",
            "incoming call", "ringing", "answer", "decline", "end call"
        )

        // 通话相关窗口的类名特征（小写比较）。语音聊天的界面类名可能也在
        // voip/calling 包下，所以带 voicechat 字样的窗口不算通话窗口。
        private val CALL_CLASS_HINTS = listOf("voip", "calling", "callactivity", "callscreen")
        private val CALL_CLASS_EXEMPT = listOf("voicechat", "conversation")

        // 优先按 viewId 匹配语音聊天控制条的退出按钮。目前留空：未经真机
        // 确认的 id 有误点通话挂断键的风险。可用 `adb shell uiautomator dump`
        // 实测后填入（注意与通话界面挂断按钮的 id 区分开），文字匹配作兜底。
        private val LEAVE_VIEW_IDS = listOf<String>()

        // 通话界面挂断按钮（仅在通知监听器确认要挂断、GuardState 窗口内使用）
        private val HANGUP_SEARCH_WORDS = listOf("挂断", "结束", "离开", "hang", "end", "leave")
        private val HANGUP_EXACT = listOf(
            "挂断", "结束", "离开", "结束通话", "离开通话", "挂断电话",
            "hang up", "end call", "leave call", "leave", "end"
        )
    }

    private var lastLeaveClickAt = 0L
    private var lastConfirmClickAt = 0L
    private var awaitingConfirm = false

    /** 当前顶层窗口是否是通话/来电界面（由 TYPE_WINDOW_STATE_CHANGED 维护） */
    private var inCallWindow = false

    override fun onServiceConnected() {
        super.onServiceConnected()
        GuardNotifications.ensureChannel(this)
        Log.i(TAG, "服务已连接")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        if (event.packageName?.toString() != WHATSAPP_PACKAGE) return

        // 防线一：通话/来电相关窗口内的事件一律忽略
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) {
            val cls = event.className?.toString()?.lowercase() ?: ""
            if (cls.isNotEmpty()) {
                inCallWindow = CALL_CLASS_HINTS.any { cls.contains(it) } &&
                    CALL_CLASS_EXEMPT.none { cls.contains(it) }
            }
        }
        if (inCallWindow) {
            // 唯一例外：通知监听器已确认这是误拨的群组通话/语音聊天并打开了
            // 通话界面（GuardState 时间窗口内）→ 点击界面上的挂断按钮
            if (SystemClock.elapsedRealtime() < GuardState.hangupUntilElapsed) {
                val callRoot = rootInActiveWindow ?: return
                if (clickHangupButton(callRoot)) {
                    GuardState.hangupUntilElapsed = 0L
                    Log.i(TAG, "已在通话界面点击挂断（后台拦截兜底）")
                }
            }
            return
        }

        val now = SystemClock.elapsedRealtime()
        val root = rootInActiveWindow ?: return

        // 防线二：屏幕上有任何通话/来电特征文字 → 不动作
        if (CALL_SCREEN_MARKERS.any {
                !root.findAccessibilityNodeInfosByText(it).isNullOrEmpty()
            }) return

        if (awaitingConfirm && now - lastLeaveClickAt > CONFIRM_WINDOW_MS) {
            awaitingConfirm = false
        }

        // 阶段二：刚点过退出，优先处理可能弹出的确认对话框（不受暂停影响，
        // 把已经开始的退出流程走完；不重复发通知）
        if (awaitingConfirm) {
            if (now - lastConfirmClickAt >= CONFIRM_DEBOUNCE_MS && clickConfirmButton(root)) {
                lastConfirmClickAt = now
                awaitingConfirm = false
                Log.i(TAG, "已点击确认对话框按钮")
            }
            return
        }

        // 暂停期内不做新的拦截
        if (isSnoozed()) return

        // 阶段一：检测本人是否处于群组语音聊天中
        if (now - lastLeaveClickAt < LEAVE_DEBOUNCE_MS) return

        if (tryLeaveVoiceChat(root)) {
            lastLeaveClickAt = now
            awaitingConfirm = true
            GuardNotifications.showIntercepted(this, getString(R.string.notif_title))
        }
    }

    /** 通话界面的挂断按钮（仅 GuardState 窗口内调用，见 onAccessibilityEvent） */
    private fun clickHangupButton(root: AccessibilityNodeInfo): Boolean {
        for (word in HANGUP_SEARCH_WORDS) {
            val nodes = root.findAccessibilityNodeInfosByText(word) ?: continue
            for (node in nodes) {
                val labels = labelsOf(node)
                if (labels.any { l -> JOIN_WORDS.any { l.contains(it, ignoreCase = true) } }) continue
                if (labels.any { l -> HANGUP_EXACT.any { h -> l.equals(h, ignoreCase = true) } }) {
                    if (clickFirstClickable(listOf(node))) return true
                }
            }
        }
        return false
    }

    private fun tryLeaveVoiceChat(root: AccessibilityNodeInfo): Boolean {
        // 防线三：必须存在「语音聊天/Voice chat」标记，否则一律不动作
        val inVoiceChatContext = VOICE_CHAT_WORDS.any {
            !root.findAccessibilityNodeInfosByText(it).isNullOrEmpty()
        }
        if (!inVoiceChatContext) return false

        // 1) 优先按 viewId 找退出按钮
        for (id in LEAVE_VIEW_IDS) {
            val nodes = root.findAccessibilityNodeInfosByViewId(id) ?: continue
            if (nodes.isNotEmpty() && clickFirstClickable(nodes)) {
                Log.i(TAG, "自动退出语音聊天（viewId: $id）")
                return true
            }
        }

        // 2) 文字兜底。没有任何「退出/Leave」类节点（例如只看到别人的
        //    「加入」气泡）→ 不动作
        val leaveNodes = LEAVE_WORDS.flatMap {
            root.findAccessibilityNodeInfosByText(it) ?: emptyList()
        }
        if (leaveNodes.isEmpty()) return false

        val candidates = leaveNodes.filter { isLeaveButton(it) }
        if (candidates.isEmpty()) return false

        if (clickFirstClickable(candidates)) {
            Log.i(TAG, "自动退出语音聊天（文字匹配）")
            return true
        }
        return false
    }

    /**
     * 判断节点是否是安全可点的「退出语音聊天」按钮：
     *  - 文字/描述含「加入/Join」→ 绝不点击
     *  - 文字同时含「退出」和「语音聊天」（如「退出语音聊天」）→ 可点
     *  - 文字完整等于「退出/Leave/离开」→ 可点（外层已确认在语音聊天场景）
     *  - 其余（如「退出群组」「退出登录」、聊天消息里的普通文字）→ 不点
     */
    private fun isLeaveButton(node: AccessibilityNodeInfo): Boolean {
        val labels = labelsOf(node)
        if (labels.isEmpty()) return false
        if (labels.any { l -> JOIN_WORDS.any { l.contains(it, ignoreCase = true) } }) return false

        return labels.any { label ->
            val leaveAndVoice = LEAVE_WORDS.any { label.contains(it, ignoreCase = true) } &&
                VOICE_CHAT_WORDS.any { label.contains(it, ignoreCase = true) }
            val exact = LEAVE_EXACT.any { label.equals(it, ignoreCase = true) }
            leaveAndVoice || exact
        }
    }

    /** 确认对话框：按钮文字必须完整匹配 CONFIRM_EXACT 之一 */
    private fun clickConfirmButton(root: AccessibilityNodeInfo): Boolean {
        val words = listOf("结束", "退出", "离开", "end", "leave")
        for (word in words) {
            val nodes = root.findAccessibilityNodeInfosByText(word) ?: continue
            for (node in nodes) {
                val labels = labelsOf(node)
                if (labels.any { l -> JOIN_WORDS.any { l.contains(it, ignoreCase = true) } }) continue
                if (labels.any { l -> CONFIRM_EXACT.any { c -> l.equals(c, ignoreCase = true) } }) {
                    if (clickFirstClickable(listOf(node))) return true
                }
            }
        }
        return false
    }

    /** 节点的文字与内容描述（去除首尾空白） */
    private fun labelsOf(node: AccessibilityNodeInfo): List<String> {
        return listOfNotNull(
            node.text?.toString()?.trim(),
            node.contentDescription?.toString()?.trim()
        ).filter { it.isNotEmpty() }
    }

    /** 点击列表中第一个可点击节点；节点本身不可点击时向上找可点击的父节点 */
    private fun clickFirstClickable(nodes: List<AccessibilityNodeInfo>): Boolean {
        for (node in nodes) {
            var cur: AccessibilityNodeInfo? = node
            var depth = 0
            while (cur != null && depth <= MAX_ANCESTOR_DEPTH) {
                if (cur.isClickable && cur.isEnabled) {
                    if (cur.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
                }
                cur = cur.parent
                depth++
            }
        }
        return false
    }

    // ---------- 暂停（snooze） ----------

    private fun isSnoozed(): Boolean {
        val until = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getLong(KEY_SNOOZE_UNTIL, 0L)
        return System.currentTimeMillis() < until
    }

    override fun onInterrupt() {
        // no-op
    }
}
