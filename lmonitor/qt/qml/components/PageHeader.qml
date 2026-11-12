import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Small grey line above a big title; anything placed inside goes to the right.
Item {
    id: root
    property string kicker: ""
    property string title: ""
    default property alias extras: rightSide.data
    height: 58
    Column {
        anchors.verticalCenter: parent.verticalCenter; spacing: 0
        Text { text: Tr.t(root.kicker); color: Tokens.sub; visible: text !== ""
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Text { text: Tr.t(root.title); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 30; font.bold: true }
    }
    Row { id: rightSide; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
          spacing: 14 }
}
