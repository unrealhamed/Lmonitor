import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

Rectangle {
    id: root
    property bool checked: false
    signal toggled(bool on)
    width: 20; height: 20; radius: 5
    color: checked ? Tokens.accent : (Tokens.light ? Tokens.card : Tokens.bg0)
    border.width: checked ? 0 : 1; border.color: ma.containsMouse ? Tokens.accent : Tokens.lineStrong
    Text { anchors.centerIn: parent; visible: root.checked; text: ""; color: Tokens.accentText
           font.family: Tokens.iconFont; font.pixelSize: 12 }
    MouseArea { id: ma; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.toggled(!root.checked) }
}
