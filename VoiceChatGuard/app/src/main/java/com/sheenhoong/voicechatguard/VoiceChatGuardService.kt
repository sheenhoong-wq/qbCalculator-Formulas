package com.sheenhoong.voicechatguard

import android.accessibilityservice.AccessibilityService
import android.os.SystemClock
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

/**
 * 监听 WhatsApp 界面，检测到本人处于群组语音聊天时自动点击「退出」。
 *
 * 安全规则：
 *  - 只有出现「退出/Leave」按钮（代表本人已加入/发起）才动作
 *  - 如果只看到「加入/Join」（别人开的语音聊天），绝不点击任何东西
 *  - 文字匹配要求整字匹配或同时含「语音聊天」字样，防止误点「退出群组」等其他按钮
 */
class VoiceChatGuardService : AccessibilityService() {

    companion object {
        private const val TAG = "VoiceChatGuard"
        private const val WHATSAPP_PACKAGE = "com.whatsapp"

        /** 点击「退出」后 3 秒内不再触发新的退出动作（防抖） */
        private const val LEAVE_DEBOUNCE_MS = 3000L

        /** 点击「退出」后，在此时间窗口内寻找并点击确认对话框 */
        private const val CONFIRM_WINDOW_MS = 8000L

        /** 两次确认按钮点击之间的最小间隔 */
        private const val CONFIRM_DEBOUNCE_MS = 800L

        /** 节点本身不可点击时，最多向上找几层父节点 */
        private const val MAX_ANCESTOR_DEPTH = 3

        // 语音聊天场景标志（包含匹配，不区分大小写）
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

        // 优先按 viewId 匹配；WhatsApp 版本不同 id 可能变化，文字匹配作为兜底。
        // 如需精确 id，可用 `adb shell uiautomator dump` 确认后补充到此列表。
        private val LEAVE_VIEW_IDS = listOf(
            "com.whatsapp:id/leave_voice_chat",
            "com.whatsapp:id/voice_chat_leave_button",
            "com.whatsapp:id/end_call_button"
        )
    }

    private var lastLeaveClickAt = 0L
    private var lastConfirmClickAt = 0L
    private var awaitingConfirm = false

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.i(TAG, "服务已连接")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent) {
        if (event.packageName?.toString() != WHATSAPP_PACKAGE) return

        val now = SystemClock.elapsedRealtime()
        val root = rootInActiveWindow ?: return

        if (awaitingConfirm && now - lastLeaveClickAt > CONFIRM_WINDOW_MS) {
            awaitingConfirm = false
        }

        // 阶段二：刚点过退出，优先处理可能弹出的确认对话框
        if (awaitingConfirm) {
            if (now - lastConfirmClickAt >= CONFIRM_DEBOUNCE_MS && clickConfirmButton(root)) {
                lastConfirmClickAt = now
                awaitingConfirm = false
                Log.i(TAG, "已点击确认对话框按钮")
            }
            return
        }

        // 阶段一：检测本人是否处于语音聊天中
        if (now - lastLeaveClickAt < LEAVE_DEBOUNCE_MS) return

        if (tryLeaveVoiceChat(root)) {
            lastLeaveClickAt = now
            awaitingConfirm = true
        }
    }

    private fun tryLeaveVoiceChat(root: AccessibilityNodeInfo): Boolean {
        // 1) 优先按 viewId 找退出按钮
        for (id in LEAVE_VIEW_IDS) {
            val nodes = root.findAccessibilityNodeInfosByViewId(id) ?: continue
            if (nodes.isNotEmpty() && clickFirstClickable(nodes)) {
                Log.i(TAG, "自动退出语音聊天（viewId: $id）")
                return true
            }
        }

        // 2) 文字兜底。先收集所有含「退出/Leave」类关键词的节点；
        //    若一个都没有（例如只看到别人的「加入」气泡），直接不动作。
        val leaveNodes = LEAVE_WORDS.flatMap {
            root.findAccessibilityNodeInfosByText(it) ?: emptyList()
        }
        if (leaveNodes.isEmpty()) return false

        // 是否处于语音聊天场景（界面上有「语音聊天/Voice chat」字样）
        val inVoiceChatContext = VOICE_CHAT_WORDS.any {
            !root.findAccessibilityNodeInfosByText(it).isNullOrEmpty()
        }

        val candidates = leaveNodes.filter { node -> isLeaveButton(node, inVoiceChatContext) }
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
     *  - 文字完整等于「退出/Leave/离开」且当前界面确实在语音聊天场景 → 可点
     *  - 其余（如「退出群组」「退出登录」、聊天消息里的普通文字）→ 不点
     */
    private fun isLeaveButton(node: AccessibilityNodeInfo, inVoiceChatContext: Boolean): Boolean {
        val labels = labelsOf(node)
        if (labels.isEmpty()) return false
        if (labels.any { l -> JOIN_WORDS.any { l.contains(it, ignoreCase = true) } }) return false

        return labels.any { label ->
            val leaveAndVoice = LEAVE_WORDS.any { label.contains(it, ignoreCase = true) } &&
                VOICE_CHAT_WORDS.any { label.contains(it, ignoreCase = true) }
            val exact = LEAVE_EXACT.any { label.equals(it, ignoreCase = true) }
            leaveAndVoice || (exact && inVoiceChatContext)
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

    override fun onInterrupt() {
        // no-op
    }
}
