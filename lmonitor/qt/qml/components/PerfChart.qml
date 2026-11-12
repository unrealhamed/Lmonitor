import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Home chart: CPU / RAM / GPU lines, real time (last 10 s) or 1 minute. The same smooth
// chart as the Graphs page.
Card {
    id: root
    property var d: ({})                    // backend.graphs(...) of the chosen span
    property real nowMs: 0
    property int rangeIndex: 0
    property var rangeNames: []
    signal rangePicked(int index)
    readonly property var colors: [Tokens.cpu, Tokens.ram, Tokens.gpu]
    readonly property var names: ["CPU", "RAM", "GPU"]

    Text {
        x: 18; y: 16; text: Tr.t("Performance"); color: Tokens.text
        font.family: Tokens.font; font.pixelSize: 18; font.bold: true
    }
    Row {                                   // legend
        x: 18; y: 44; spacing: 16
        Repeater {
            model: 3
            Row {
                spacing: 6
                Rectangle { width: 8; height: 8; radius: 4; y: 4; color: root.colors[index] }
                Text { text: root.names[index]; color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
            }
        }
    }
    Row {                                   // time span
        anchors.right: parent.right; anchors.rightMargin: 14; y: 12; spacing: 4
        Repeater {
            model: root.rangeNames
            Rectangle {
                width: tabText.width + 26; height: 28; radius: 9
                color: index === root.rangeIndex ? Tokens.accentA(0.20) : "transparent"
                border.width: 1
                border.color: index === root.rangeIndex ? Tokens.accent : Tokens.line
                Text { id: tabText; anchors.centerIn: parent; text: Tr.t(modelData)
                       color: index === root.rangeIndex ? Tokens.text : Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.rangePicked(index) }
            }
        }
    }
    GraphChart {
        x: 14; y: 76; width: root.width - 30; height: root.height - 76 - 18
        series: [root.d.c_use || [], root.d.r_use || [], root.d.g_use || []]
        colors: root.colors; fill: false; maxValue: 100; unit: "%"
        slots: root.d.points || 60; slotMs: root.d.slot_ms || 1000
        scrollEnd: root.d.end_ms || 0; extra: root.d.extra || 0
        delayMs: root.d.delay_ms || 0; nowMs: root.nowMs
    }
}
