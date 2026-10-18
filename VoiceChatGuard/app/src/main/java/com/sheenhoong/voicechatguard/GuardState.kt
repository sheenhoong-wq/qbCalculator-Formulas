package com.sheenhoong.voicechatguard

/**
 * 通知监听器与无障碍服务之间的进程内共享状态。
 *
 * 通知上没有「挂断」按钮时，通知监听器会打开通话界面并设置一个短暂的
 * 时间窗口，由无障碍服务在窗口内点击界面上的挂断按钮。
 */
object GuardState {
    /** SystemClock.elapsedRealtime() 截止时间；在此之前允许无障碍服务点挂断 */
    @Volatile
    var hangupUntilElapsed = 0L
}
