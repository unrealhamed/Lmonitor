import QtQuick
import Lmonitor
import "../components"

// Live charts of what the engine keeps in memory (about the last minutes of
// this session). Min / average / max are computed from the same readings.
// A sensor that reports nothing shows "No sensor data" instead of a flat line.
Item {
    id: page
    property var charts: backend.charts()
    readonly property var net: backend.dashboard && backend.dashboard.ready ? backend.dashboard.network : null
    readonly property int g: Tokens.gap
    Connections {
        target: backend
        function onDashboardChanged() { page.charts = backend.charts() }
    }
    function stat(vals) {
        var n = 0, sum = 0, mn = 1e9, mx = -1e9, last = null
        for (var i = 0; i < vals.length; ++i) {
            var v = vals[i]
            if (v === null || v === undefined) continue
            n++; sum += v; if (v < mn) mn = v; if (v > mx) mx = v; last = v
        }
        return n ? {n: n, last: last, min: mn, avg: sum / n, max: mx} : {n: 0}
    }
    function byKey(k) { for (var i = 0; i < charts.length; ++i) if (charts[i].key === k) return charts[i]; return {values: [], title: "", unit: ""} }
    readonly property var tiles: [
        {key: "c_use", title: "CPU usage", color: Tokens.cpu, max: 100},
        {key: "g_use", title: "GPU usage", color: Tokens.gpu, max: 100},
        {key: "r_use", title: "RAM usage", color: Tokens.ram, max: 100},
        {key: "c_temp", title: "CPU temperature", color: Tokens.orange, max: 100},
        {key: "g_temp", title: "GPU temperature", color: Tokens.orange, max: 100},
        {key: "net", title: "Download speed", color: Tokens.violet, max: 0}
    ]

    PageHeader { id: head; width: parent.width; kicker: "Live while this window is open"; title: "Performance" }

    Grid {
        y: head.height + 12; width: parent.width; height: parent.height - y
        columns: 3; spacing: page.g
        Repeater {
            model: page.tiles
            Card {
                id: tile
                width: (parent.width - 2 * page.g) / 3
                height: (parent.height - page.g) / 2
                readonly property bool isNet: modelData.key === "net"
                readonly property var ch: isNet ? ({values: page.net ? page.net.hist : [], unit: ""}) : page.byKey(modelData.key)
                readonly property var st: page.stat(ch.values)
                readonly property string unit: isNet ? "" : ch.unit
                Text { x: 20; y: 16; text: modelData.title; color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                Text { x: 20; y: 38
                       text: tile.isNet ? (page.net ? page.net.down : "--")
                             : (tile.st.n ? Math.round(tile.st.last) + (tile.unit === "%" ? "%" : " " + tile.unit) : "--")
                       color: Tokens.text; font.family: Tokens.font; font.pixelSize: 34; font.bold: true }
                Row {
                    x: 20; y: 86; spacing: 18; visible: tile.st.n > 0 && !tile.isNet
                    Repeater {
                        model: [["MIN", tile.st.min], ["AVG", tile.st.avg], ["MAX", tile.st.max]]
                        Column {
                            Text { text: modelData[0]; color: Tokens.dim
                                   font.family: Tokens.font; font.pixelSize: 10; font.bold: true }
                            Text { text: Math.round(modelData[1]) + tile.unit; color: Tokens.sub
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                        }
                    }
                }
                Text { x: 20; y: 86; visible: tile.isNet && page.net !== null
                       text: "Upload  " + (page.net ? page.net.up : ""); color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                AreaChart {
                    visible: tile.st.n > 0
                    x: 16; y: 126; width: parent.width - 32; height: parent.height - 126 - 18
                    values: tile.ch.values; color: modelData.color
                    maxValue: modelData.max; unit: tile.unit === "°C" ? "°" : (tile.unit === "%" ? "%" : "")
                }
                Text { visible: tile.st.n === 0; anchors.centerIn: parent
                       text: "No sensor data"; color: Tokens.dim
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
            }
        }
    }
}
