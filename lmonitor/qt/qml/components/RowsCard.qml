import QtQuick
import Lmonitor

// One titled section of label/value rows (Hardware, session details).
// rows: [{kind: "row"|"bar", a, b, c}]. A row with no value is a full-width
// paragraph. c = a "#rrggbb" colour (row) or a 0..1 fraction (bar).
Card {
    id: sec
    property string title: ""
    property var rows: []
    height: 60 + body.implicitHeight
    Text { x: 20; y: 16; visible: sec.title !== ""; text: Tr.t(sec.title); color: Tokens.accent
           width: parent.width - 40; elide: Text.ElideRight
           font.family: Tokens.font; font.pixelSize: 15; font.bold: true }
    Column {
        id: body
        x: 20; y: sec.title !== "" ? 46 : 16; width: parent.width - 40
        Repeater {
            model: sec.rows
            Item {
                width: body.width
                height: Math.max(val.implicitHeight, 20) + 12
                Rectangle { visible: index > 0; width: parent.width; height: 1; color: "#1e1e23" }
                Text { visible: modelData.b === ""; x: 0; y: 8; width: parent.width; wrapMode: Text.Wrap
                       text: Tr.t(modelData.a); color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                Text { visible: modelData.b !== ""; x: 0; y: 8; width: parent.width * 0.38; text: Tr.t(modelData.a)
                       color: Tokens.dim; elide: Text.ElideRight
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                Text { id: val; visible: modelData.b !== ""; x: parent.width * 0.40; y: 8; width: parent.width * 0.60
                       horizontalAlignment: Text.AlignRight; wrapMode: Text.Wrap
                       text: Tr.t(modelData.b)
                       color: modelData.kind === "row" && typeof modelData.c === "string" && modelData.c.charAt(0) === "#" ? modelData.c : Tokens.text
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                Rectangle { visible: modelData.kind === "bar" && modelData.c !== null
                            x: 0; y: parent.height - 5; width: parent.width; height: 3; radius: 2; color: "#2a2a31"
                    Rectangle { height: parent.height; radius: 2; color: Tokens.accent
                                width: parent.width * Math.max(0, Math.min(1, Number(modelData.c) || 0)) } }
            }
        }
    }
}
