import QtQuick
import Lmonitor

// What the last action did: title, before -> after, message. Shown until closed.
Card {
    id: root
    property var result: null
    signal dismissed()
    visible: result !== null && result !== undefined && !!result.title
    height: visible ? 24 + col.implicitHeight : 0
    Rectangle { x: 0; y: 0; width: 4; height: parent.height; radius: 2
                color: root.result && root.result.ok === false ? Tokens.danger : Tokens.accent }
    Column {
        id: col; x: 20; y: 12; width: parent.width - 80; spacing: 4
        Text { width: parent.width; elide: Text.ElideRight; color: Tokens.text
               text: root.result ? Tr.t(root.result.title) : ""
               font.family: Tokens.font; font.pixelSize: 15; font.bold: true }
        Text { visible: !!(root.result && (root.result.before || root.result.after)); width: parent.width
               wrapMode: Text.Wrap; color: Tokens.sub
               text: root.result ? ((root.result.before || "") + (root.result.after ? "   →   " + root.result.after : "")) : ""
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Text { width: parent.width; wrapMode: Text.Wrap; color: Tokens.dim
               text: root.result && root.result.message ? Tr.t(root.result.message) : ""
               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
    }
    Text { anchors.right: parent.right; anchors.rightMargin: 18; y: 10; text: "✕"; color: Tokens.dim
           font.pixelSize: 16
           MouseArea { anchors.fill: parent; anchors.margins: -8; cursorShape: Qt.PointingHandCursor
                       onClicked: root.dismissed() } }
}
