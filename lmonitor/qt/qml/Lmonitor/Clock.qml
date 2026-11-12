pragma Singleton
import QtQuick

// One shared per-frame clock for every moving chart (instead of one animation per chart).
// It only runs while a page with moving charts is on screen, so a minimized window or a
// page without charts costs nothing.
QtObject {
    id: clk
    property real now: Date.now()
    property bool active: true
    // At most ~70 steps a second: on a 120 / 144 / 165 Hz screen every frame was redrawn,
    // which looks the same as every other frame but costs twice the work.
    property FrameAnimation ticker: FrameAnimation {
        running: clk.active
        onTriggered: { var t = Date.now(); if (t - clk.now >= 14) clk.now = t }
    }
}
