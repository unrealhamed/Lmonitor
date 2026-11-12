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
    // The window only grows while the numbers change (99 -> 100 fps, 9 -> 10 W...).
    // Resizing an always-on-top window over a game every half second costs the game
    // frames, so it shrinks only when the settings change.
    property real keepW: 1
    property real keepH: 1
    width: keepW
    height: keepH
    function grow() {
        if (bar.implicitWidth > keepW) keepW = bar.implicitWidth
        if (bar.implicitHeight > keepH) keepH = bar.implicitHeight
    }
    function fit() { keepW = Math.max(1, bar.implicitWidth); keepH = Math.max(1, bar.implicitHeight) }
    Connections {
        target: bar
        function onImplicitWidthChanged() { w.grow() }
        function onImplicitHeightChanged() { w.grow() }
    }
    Connections {
        target: backend
        function onSettingsChanged() { w.fit() }
    }
    Component.onCompleted: fit()
    title: Tr.t("Lmonitor overlay")

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
