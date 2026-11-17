import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Choice of a few options. model: list of strings; `index` is the selected one (-1 = none).
// The track is sunk into the card; the chosen option is a raised tile.
Rectangle {
    id: root
    property var model: []
    property int index: 0
    signal picked(int i)
    height: 36; radius: 9
    color: Tokens.bg0
    border.width: 1; border.color: Tokens.line
    Row {
        anchors.fill: parent; anchors.margins: 3; spacing: 2
        Repeater {
            model: root.model
            Rectangle {
                readonly property bool on: index === root.index
                width: (root.width - 6 - 2 * (root.model.length - 1)) / root.model.length; height: parent.height
                radius: 7
                color: on ? (Tokens.light ? Tokens.card : Tokens.raised)
                          : (segMouse.containsMouse ? Tokens.fg(0.04) : "transparent")
                border.width: on ? 1 : 0; border.color: Tokens.line
                Text { anchors.centerIn: parent; text: Tr.t(modelData)
                       color: parent.on ? Tokens.text : Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                       font.weight: parent.on ? Font.DemiBold : Font.Medium }
                MouseArea { id: segMouse; anchors.fill: parent; hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor; onClicked: root.picked(index) }
            }
        }
    }
}
