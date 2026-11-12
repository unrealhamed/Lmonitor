import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Pill selector. model: list of strings; `index` is the selected one (-1 = none).
Rectangle {
    id: root
    property var model: []
    property int index: 0
    signal picked(int i)
    height: 36; radius: 12
    color: Tokens.fg(0.05)
    border.width: 1; border.color: Tokens.line
    Row {
        anchors.fill: parent; anchors.margins: 3
        Repeater {
            model: root.model
            Rectangle {
                width: (root.width - 6) / root.model.length; height: parent.height
                radius: 9
                color: index === root.index ? Tokens.accentA(0.20) : "transparent"
                border.width: index === root.index ? 1 : 0
                border.color: Tokens.accent
                Text { anchors.centerIn: parent; text: Tr.t(modelData)
                       color: index === root.index ? Tokens.text : Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.picked(index) }
            }
        }
    }
}
