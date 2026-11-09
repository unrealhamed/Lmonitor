pragma Singleton
import QtQuick

// One shared per-frame clock for every moving chart (instead of one animation per chart).
// It only runs while a page with moving charts is on screen, so a minimized window or a
// page without charts costs nothing.
QtObject {
    id: clk
    property real now: Date.now()
    property bool active: true
    property FrameAnimation ticker: FrameAnimation {
        running: clk.active
        onTriggered: clk.now = Date.now()
    }
}
