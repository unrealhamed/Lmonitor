import QtQuick
import QtQuick.Window
import Lmonitor
import "components"

// The real overlay: a frameless, transparent, always-on-top window.
// Python (OverlayHost) places it, makes it click-through and handles F9 /
// move mode. In move mode the bar can be dragged; right-click ends it.
Window {
    id: w
    visible: false
    color: "transparent"
    width: bar.implicitWidth
    height: bar.implicitHeight
    title: "Lmonitor overlay"

    OverlayBar {
        id: bar
        anchors.fill: parent
        model: backend.overlay
        style: backend.settings
    }
    Rectangle {                         // move-mode outline
        anchors.fill: parent
        visible: backend.moving
        color: "transparent"
        radius: 10
        border.width: 2
        border.color: Tokens.cyan
    }
    MouseArea {
        anchors.fill: parent
        enabled: backend.moving
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onPressed: function (m) {
            if (m.button === Qt.RightButton) backend.setMoving(false)
            else w.startSystemMove()
        }
        onReleased: backend.saveMoved()
    }
}
