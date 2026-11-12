import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Real-time performance: CPU / RAM / GPU lines and the time-range tabs.
Card {
    id: root
    property var series: [[], [], []]       // [cpu, ram, gpu]
    property int rangeIndex: 0
    property var rangeNames: []
    signal rangePicked(int index)
    readonly property var colors: [Tokens.cpu, Tokens.ram, Tokens.gpu]
    readonly property var names: ["CPU", "RAM", "GPU"]
    readonly property int longest: {
        var m = 2
        for (var i = 0; i < series.length; ++i) m = Math.max(m, (series[i] || []).length)
        return m
    }

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
    Row {                                   // range tabs (all real)
        anchors.right: parent.right; anchors.rightMargin: 14; y: 12; spacing: 4
        Repeater {
            model: root.rangeNames
            Rectangle {
                width: 54; height: 28; radius: 9
                color: index === root.rangeIndex ? Tokens.accentA(0.20) : "transparent"
                border.width: 1
                border.color: index === root.rangeIndex ? Tokens.accent : Tokens.line
                Text { anchors.centerIn: parent; text: Tr.t(modelData)
                       color: index === root.rangeIndex ? Tokens.text : Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.rangePicked(index) }
            }
        }
    }
    Repeater {                              // y axis labels
        model: ["100", "50", "0"]
        Text { x: 14; y: 72 + (root.height - 72 - 18) * index / 2 - 7
               text: modelData; color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: 10 }
    }
    Repeater {                              // grid
        model: 3
        Rectangle { x: 46; width: root.width - 46 - 16; height: 1; color: Tokens.line
                    y: 72 + Math.round((root.height - 72 - 18 - 1) * index / 2) }
    }
    LiveCanvas {
        x: 46; y: 72; width: root.width - 46 - 16; height: root.height - 72 - 18
        series: root.series; colors: root.colors; fill: false
        maxValue: 100
        slide: root.rangeIndex === 0
        slots: root.rangeIndex === 0 ? Math.max(2, Math.round(60000 / backend.interval)) : root.longest
        interval: backend.interval
    }
}
