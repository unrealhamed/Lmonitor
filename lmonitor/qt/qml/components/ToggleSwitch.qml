import QtQuick
import Lmonitor

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool on)
    width: 46; height: 26; radius: 13
    color: checked ? Tokens.accent : Tokens.fg(0.14)
    Behavior on color { ColorAnimation { duration: 120 } }
    Rectangle {
        y: 3; width: 20; height: 20; radius: 10; color: "white"
        x: root.checked ? parent.width - width - 3 : 3
        Behavior on x { NumberAnimation { duration: 120 } }
    }
    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                onClicked: root.toggled(!root.checked) }
}
