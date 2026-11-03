import QtQuick
import Lmonitor
import "../components"

Item {
    id: page
    PageHeader { id: head; width: parent.width; kicker: "Gaming overlay and system monitor"; title: "About" }
    Card {
        y: head.height + 12; width: Math.min(parent.width, 720); height: col.height + 44; tint: true
        Column {
            id: col
            x: 24; y: 22; width: parent.width - 48; spacing: 14
            Text { text: "Lmonitor"; color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: 26; font.bold: true }
            Text { text: "Version " + backend.version; color: Tokens.accent
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 14; lineHeight: 1.25
                   text: "Lmonitor is a gaming overlay and system monitor for Windows. It shows FPS, CPU, GPU, RAM and network readings on top of your game, and keeps a record of your play sessions." }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 14; lineHeight: 1.25
                   text: "Made by a new developer named unrealhamed." }
            Text { textFormat: Text.RichText; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 14
                   text: "GitHub: <a href=\"https://github.com/unrealhamed/Lmonitor\" style=\"color:" + Tokens.accent + "\">github.com/unrealhamed/Lmonitor</a>"
                   onLinkActivated: function (l) { Qt.openUrlExternally(l) }
                   MouseArea { anchors.fill: parent; acceptedButtons: Qt.NoButton
                               cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor } }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                   text: "This is the new interface. Sensors, sessions and the overlay come from the same engine as the classic window, and both share the same settings." }
        }
    }
}
