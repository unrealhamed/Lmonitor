import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// One of the four cards at the top of Home: icon, name, status, a big number, details,
// and either a temperature gauge (CPU / GPU) or a fill bar (memory / storage).
Card {
    id: root
    property string title: ""
    property string caption: ""        // small grey line under the name
    property string glyph: ""          // Windows icon font code
    property color tone: Tokens.cyan   // the metric's own color
    property string status: "none"
    property string big: "--"
    property string bigUnit: ""
    property string line1: ""
    property string line2: ""
    property string warning: ""        // e.g. why the CPU temperature is missing
    property bool gauge: false
    property var gaugeValue: null
    property real bar: -1              // 0..1, or -1 = no bar

    Rectangle {
        x: 18; y: 16; width: 34; height: 34; radius: 9; color: Tokens.tint(root.tone, 0.14)
        Text { anchors.centerIn: parent; text: root.glyph; color: root.tone
               font.family: Tokens.iconFont; font.pixelSize: 17 }
    }
    Column {
        x: 62; y: 17; width: parent.width - 62 - badge.width - 24; spacing: 1
        Text { text: Tr.t(root.title); color: Tokens.text; width: parent.width; elide: Text.ElideRight
               font.family: Tokens.font; font.pixelSize: 14; font.weight: Font.DemiBold }
        Text { text: Tr.t(root.caption); color: Tokens.dim; width: parent.width; elide: Text.ElideRight
               font.family: Tokens.font; font.pixelSize: 12 }
    }
    Rectangle {
        id: badge
        anchors.right: parent.right; anchors.rightMargin: 18; y: 20
        readonly property color c: root.status === "none" ? Tokens.dim : Tokens.statusColor(root.status)
        // narrow cards: only the colored dot, so the name is not cut off
        width: root.width >= 250 ? badgeRow.width + 16 : 22; height: 22; radius: 6; color: Tokens.tint(c, 0.13)
        Row { id: badgeRow; anchors.centerIn: parent; spacing: 6
              Rectangle { width: 7; height: 7; radius: 4; color: badge.c; anchors.verticalCenter: parent.verticalCenter }
              Text { visible: root.width >= 250; text: Tokens.statusText(root.status); color: badge.c
                     font.family: Tokens.font; font.pixelSize: 12; font.weight: Font.DemiBold } }
    }
    Column {
        x: 18; y: root.gauge && root.bar < 0 ? 66 : 54; width: parent.width - 36 - (root.gauge ? 86 : 0); spacing: 1
        Row {
            spacing: 2
            Text { text: root.big; color: Tokens.text
                   font.family: Tokens.fontDisplay; font.pixelSize: root.bar >= 0 && root.gauge ? 30 : 34; font.weight: Font.DemiBold }
            Text { anchors.baseline: parent.children[0].baseline; text: root.bigUnit; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 15; font.weight: Font.DemiBold }
        }
        Text { text: Tr.line(root.line1); color: Tokens.dim; width: parent.width; elide: Text.ElideRight
               font.family: Tokens.font; font.pixelSize: 12 }
        Text { visible: text !== ""; text: root.warning !== "" ? Tr.t(root.warning) : Tr.line(root.line2)
               color: root.warning !== "" ? Tokens.warn : Tokens.sub; width: parent.width; elide: Text.ElideRight
               font.family: Tokens.font; font.pixelSize: 12; font.weight: Font.DemiBold }
    }
    Gauge { visible: root.gauge; anchors.right: parent.right; anchors.rightMargin: 16
            // fits small tiles too (gauge + bar together): never runs into the bar at the bottom
            readonly property real sz: Math.min(76, root.height - (root.bar >= 0 ? 88 : 80))
            y: root.bar >= 0 ? 54 : 70; width: sz; height: sz; value: root.gaugeValue
            color: root.status === "hot" ? Tokens.danger : root.status === "warm" ? Tokens.warn : root.tone }
    Rectangle {
        visible: root.bar >= 0
        x: 18; y: parent.height - 24; width: parent.width - 36; height: 6; radius: 3; color: Tokens.lineStrong
        Rectangle { height: parent.height; radius: 3; color: root.tone
                    width: parent.width * Math.max(0, Math.min(1, root.bar))
                    Behavior on width { NumberAnimation { duration: 250 } } }
    }
}
