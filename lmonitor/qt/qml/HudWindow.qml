import QtQuick
import QtQuick.Window
import Lmonitor
import "components"

// A graph overlay window (there are two, `slot` 0 and 1): frameless, transparent, always
// on top, click-through. It floats: put the mouse on its top edge and drag (Python's
// HudHost lets the window take the mouse only then). Its size depends on the settings
// only, so new numbers never resize it over the game.
Window {
    id: w
    property int slot: 0
    readonly property var st: backend.hudStates[slot] || ({grab: false})
    visible: false
    color: "transparent"
    width: hudView.implicitWidth
    height: hudView.implicitHeight
    title: Tr.t("Lmonitor graph overlay")

    GraphHud {
        id: hudView
        animate: w.visible              // hidden (off / F10): its scroll clock stops
        info: backend.huds[w.slot] || ({items: [], accent: "#35d6ff"})
        style: backend.hudStyles[w.slot] || ({})
    }
    Rectangle {                         // outline + grip while it can be dragged
        anchors.fill: parent
        visible: w.st.grab
        color: "transparent"
        border.width: 2
        border.color: hudView.accent
        Rectangle {
            width: parent.width; height: 6
            color: hudView.accent
            Row {
                anchors.centerIn: parent; spacing: 4
                Repeater { model: 5; Rectangle { width: 3; height: 3; radius: 2; color: "#101014" } }
            }
        }
    }
    MouseArea {
        anchors.fill: parent
        enabled: w.st.grab
        cursorShape: Qt.SizeAllCursor
        onPressed: w.startSystemMove()  // Python saves the new place when the button is released
    }
}
