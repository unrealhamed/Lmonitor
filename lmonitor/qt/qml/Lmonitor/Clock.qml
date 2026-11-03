pragma Singleton
import QtQuick

// One shared timer for every sliding chart (instead of one animation per chart).
// It only runs while the main window is visible and in front, so a minimized
// window or a game in front costs nothing.
QtObject {
    id: clk
    property real now: Date.now()
    property bool active: true
    property Timer ticker: Timer {
        interval: 40; repeat: true; running: clk.active
        onTriggered: clk.now = Date.now()
    }
}
