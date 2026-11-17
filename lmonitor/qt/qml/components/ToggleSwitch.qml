import QtQuick
import Lmonitor

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool on)
    width: 40; height: 22; radius: 11
    opacity: enabled ? 1 : 0.45
    color: checked ? (ma.containsMouse ? Tokens.accentHover : Tokens.accent) : Tokens.lineStrong
    Behavior on color { ColorAnimation { duration: 120 } }
    Rectangle {
        y: 3; width: 16; height: 16; radius: 8; color: "white"
        x: root.checked ? parent.width - width - 3 : 3
        Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
    }
    MouseArea { id: ma; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true; enabled: root.enabled
                cursorShape: Qt.PointingHandCursor; onClicked: root.toggled(!root.checked) }
}
