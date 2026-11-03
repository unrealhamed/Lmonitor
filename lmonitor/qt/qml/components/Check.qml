import QtQuick
import Lmonitor

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool on)
    width: 22; height: 22; radius: 6
    color: checked ? Tokens.accent : "transparent"
    border.width: 1; border.color: checked ? Tokens.accent : Tokens.line
    Text { anchors.centerIn: parent; visible: root.checked; text: "✓"; color: "#06231a"
           font.pixelSize: 14; font.bold: true }
    MouseArea { anchors.fill: parent; anchors.margins: -4; cursorShape: Qt.PointingHandCursor
                onClicked: root.toggled(!root.checked) }
}
