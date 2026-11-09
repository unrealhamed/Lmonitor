import QtQuick
import Lmonitor

// One hardware card. `info` comes from backend.dashboard.cards.<name>.
// Missing values show "--" and "No data" - never a guess.
Card {
    id: root
    property string title: ""
    property var info: ({})
    property string sub: ""          // e.g. "52 °C"
    property string sub2: ""         // e.g. "4.2 GHz"
    property bool bar: false         // storage: usage bar instead of a chart
    readonly property var use: info && info.use !== undefined ? info.use : null
    readonly property string status: info && info.status ? info.status : "none"

    Text {
        x: 16; y: 14
        text: Tr.t(root.title)
        color: Tokens.text
        font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.bold: true
    }
    Text {
        x: parent.width - width - 16; y: 16
        text: Tokens.statusText(root.status)
        color: Tokens.statusColor(root.status)
        font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true
    }
    Text {
        x: 16; y: 40
        text: root.use === null ? "--" : Math.round(root.use) + "%"
        color: Tokens.text
        font.family: Tokens.font; font.pixelSize: Tokens.fsBig; font.bold: true
    }
    Text {
        x: 16; y: 90
        text: Tr.t(root.sub)
        color: Tokens.sub
        font.family: Tokens.font; font.pixelSize: Tokens.fsBody
    }
    Text {
        x: 16; y: 110
        text: Tr.t(root.sub2)
        color: Tokens.dim
        font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
    }
    Sparkline {
        visible: !root.bar
        x: 8; y: parent.height - 50; width: parent.width - 16; height: 42
        values: root.info && root.info.hist ? root.info.hist : []
        color: root.accent
    }
    Rectangle {                       // storage usage bar
        visible: root.bar
        x: 16; y: parent.height - 26; width: parent.width - 32; height: 8; radius: 4
        color: Tokens.line
        Rectangle {
            width: root.use === null ? 0 : parent.width * Math.min(100, root.use) / 100
            height: parent.height; radius: 4
            color: Tokens.statusColor(root.status) === Tokens.dim ? root.accent
                 : (root.status === "ok" ? root.accent : Tokens.statusColor(root.status))
        }
    }
}
