import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Hardware card in the reference style: title, model, status, usage bar.
// ring = true adds the temperature ring (CPU / GPU). Missing values show "--".
Card {
    id: root
    property string title: ""
    property string model: ""
    property var info: ({})
    property bool ring: false
    property string detail: ""        // small line under the status (clock, GB ...)
    property color ringColor: Tokens.cyan
    readonly property string status: info && info.status ? info.status : "none"
    readonly property var use: info && info.use !== undefined ? info.use : null

    Text { x: 18; y: 16; text: root.title; color: Tokens.text
           font.family: Tokens.font; font.pixelSize: 18; font.bold: true }
    Text { x: 18; y: 40; width: parent.width - (root.ring ? 130 : 36); elide: Text.ElideRight
           text: Tr.line(root.model); color: Tokens.dim
           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
    Row { x: 18; y: 62; spacing: 7
          Dot { anchors.verticalCenter: parent.verticalCenter; status: root.status }
          Text { text: Tokens.statusText(root.status); color: Tokens.text
                 font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true } }
    Text { x: 18; y: 84; width: parent.width - (root.ring ? 130 : 36); elide: Text.ElideRight
           text: Tr.t(root.detail); color: Tokens.sub
           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
    Text { visible: text !== ""; x: 18; y: 102; width: parent.width - 36; elide: Text.ElideRight
           text: root.info && root.info.note ? Tr.t(root.info.note) : ""
           color: Tokens.warn; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
    Ring { visible: root.ring; x: parent.width - 108; y: 14; width: 92; height: 92
           value: root.info && root.info.temp !== undefined ? root.info.temp : null
           color: root.status === "hot" ? Tokens.danger : (root.status === "warm" ? Tokens.warn : root.ringColor) }
    UsageBar { x: 18; y: parent.height - 48; width: parent.width - 36; value: root.use }
}
