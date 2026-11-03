import QtQuick
import Lmonitor

Rectangle {
    id: root
    property string label: ""
    property bool active: false
    signal clicked()
    height: 46; radius: 12
    border.width: active ? 1 : 0
    border.color: Tokens.accentA(0.55)
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0.0; color: root.active ? Tokens.accentA(0.28) : (hover.containsMouse ? Tokens.fg(0.05) : "transparent") }
        GradientStop { position: 1.0; color: root.active ? Tokens.accentA(0.06) : (hover.containsMouse ? Tokens.fg(0.05) : "transparent") }
    }
    Rectangle { x: 14; anchors.verticalCenter: parent.verticalCenter; width: 8; height: 8; radius: 4
                color: root.active ? Tokens.accent : Tokens.dim }
    Text { anchors.verticalCenter: parent.verticalCenter; x: 34
           text: root.label; color: root.active ? Tokens.text : Tokens.sub
           font.family: Tokens.font; font.pixelSize: Tokens.fsBody + 1; font.bold: root.active }
    MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
