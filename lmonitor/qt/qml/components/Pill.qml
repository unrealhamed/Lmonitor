import QtQuick
import Lmonitor

// Button. primary = green, otherwise a quiet dark button.
Rectangle {
    id: root
    property string label: ""
    property bool primary: false
    property bool danger: false
    signal clicked()
    implicitWidth: txt.implicitWidth + 36
    height: 38; radius: 12
    color: primary ? Tokens.accent : (danger ? Qt.rgba(1, 0.36, 0.42, 0.14)
           : (ma.containsMouse ? Tokens.fg(0.10) : Tokens.fg(0.06)))
    border.width: primary ? 0 : 1
    border.color: danger ? Tokens.danger : Tokens.line
    Text { id: txt; anchors.centerIn: parent; text: root.label
           color: root.primary ? Tokens.accentText : Tokens.text
           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
