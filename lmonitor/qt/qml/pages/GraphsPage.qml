import QtQuick
import Lmonitor
import "../components"

// CPU / GPU temperature and usage, and fan speed, for the last 1 / 5 / 10 minutes.
// Click a chart to enlarge it; in the large view the chips add or remove other lines on the
// same chart. Fan speeds are read only while this page is open, so the fan graph starts
// when you open the page. A sensor that reports nothing shows "No sensor data".
Item {
    id: page
    property int range: 1
    readonly property var secs: [60, 300, 600]
    readonly property var names: ["1 min", Tr.t("5 min"), Tr.t("10 min")]
    readonly property real slotMs: secs[range] * 1000 / 60
    property var d: backend.graphs(secs[range])
    readonly property real nowMs: Clock.now
    readonly property int g: Tokens.gap
    readonly property var metrics: [
        {key: "c_temp", title: Tr.t("CPU temperature"), unit: "°C", color: Tokens.orange},
        {key: "g_temp", title: Tr.t("GPU temperature"), unit: "°C", color: "#ff7eb6"},
        {key: "r_use", title: Tr.t("RAM usage"), unit: "%", color: Tokens.ram},
        {key: "c_use", title: Tr.t("CPU usage"), unit: "%", color: Tokens.cpu},
        {key: "g_use", title: Tr.t("GPU usage"), unit: "%", color: Tokens.gpu},
        {key: "net_down", title: Tr.t("Download"), unit: "net", color: "#a3e635"}
    ]
    readonly property var upload: ({key: "net_up", title: Tr.t("Upload"), unit: "net", color: "#facc15"})
    readonly property real netMax: {
        var m = 0, all = [d.net_down || [], d.net_up || []]
        for (var i = 0; i < 2; ++i)
            for (var j = 0; j < all[i].length; ++j) if (all[i][j] > m) m = all[i][j]
        return Math.max(1024, m * 1.15)
    }
    readonly property var fanNames: Object.keys(d.fans || {})
    readonly property var fanColors: [Tokens.green, "#7ee0d0", Tokens.warn, "#c8d0e0"]
    readonly property var fanSeries: fanNames.map(function (n) { return d.fans[n] })
    readonly property real fanMax: {
        var m = 0
        for (var i = 0; i < fanSeries.length; ++i)
            for (var j = 0; j < fanSeries[i].length; ++j) if (fanSeries[i][j] > m) m = fanSeries[i][j]
        return Math.max(500, Math.ceil(m / 500) * 500)
    }
    readonly property var allMetrics: metrics.concat([upload], fanNames.map(function (n, i) {
        return {key: "fan:" + n, title: n, unit: "RPM", color: fanColors[i % fanColors.length]}
    }))
    function last(vals) {
        for (var i = vals.length - 1; i >= 0; --i) if (vals[i] !== null && vals[i] !== undefined) return vals[i]
        return null
    }
    function values(key) {
        return (key.indexOf("fan:") === 0 ? (d.fans || {})[key.substring(4)] : d[key]) || []
    }
    function valueText(m) {
        var v = last(values(m.key))
        if (v === null) return "--"
        if (m.unit === "net") return Tokens.fmtNet(v, backend.settings.net_unit)
        return Math.round(v) + (m.unit === "%" ? "%" : " " + m.unit)
    }
    function refresh() { d = backend.graphs(secs[range]) }
    Connections { target: backend; function onDashboardChanged() { page.refresh() } }
    Component.onCompleted: backend.setGraphsOpen(true)
    Component.onDestruction: backend.setGraphsOpen(false)

    // ---- large view: the lines on it, the first one clicked comes first
    property var openKeys: []
    readonly property var openItems: allMetrics.filter(function (m) { return page.openKeys.indexOf(m.key) >= 0 })
    readonly property bool isOpen: openItems.length > 0
    // Lines of different kinds share the chart: temperature and % use 0-100, the others
    // are drawn on their own scale, shown on the right when there is exactly one more.
    function kindOf(m) { return m.unit === "RPM" ? "rpm" : m.unit === "net" ? "net" : "pct" }
    function maxOf(k) { return k === "rpm" ? fanMax : k === "net" ? netMax : 100 }
    readonly property var openKinds: {
        var out = []
        openItems.forEach(function (m) { var k = page.kindOf(m); if (out.indexOf(k) < 0) out.push(k) })
        return out.indexOf("pct") > 0 ? ["pct"].concat(out.filter(function (k) { return k !== "pct" })) : out
    }
    readonly property string mainKind: openKinds.length ? openKinds[0] : "pct"
    readonly property string sideKind: openKinds.length === 2 ? openKinds[1] : ""
    readonly property string openUnit: {
        var o = openItems.filter(function (m) { return page.kindOf(m) === "pct" })
        if (mainKind !== "pct" || o.length === 0) return ""
        if (o.every(function (m) { return m.unit === "°C" })) return "°"
        return o.every(function (m) { return m.unit === "%" }) ? "%" : ""
    }
    readonly property var openSeries: openItems.map(function (m) {
        var v = page.values(m.key), k = page.kindOf(m)
        if (k === page.mainKind) return v
        var f = page.maxOf(page.mainKind) / page.maxOf(k)
        return v.map(function (x) { return x === null || x === undefined ? null : x * f })
    })
    function open(key) { openKeys = [key]; large.forceActiveFocus() }
    function close() { openKeys = [] }
    function toggle(key) {
        var i = openKeys.indexOf(key), k = openKeys.slice()
        if (i < 0) k.push(key)
        else if (k.length > 1) k.splice(i, 1)       // the last line stays
        openKeys = k
    }

    PageHeader {
        id: head; width: parent.width; kicker: Tr.t("Live while this window is open"); title: Tr.t("Graphs")
        Segmented { width: 240; model: page.names; index: page.range
                    onPicked: function (i) { page.range = i; page.refresh() } }
    }

    readonly property real y0: head.height + 12
    readonly property real cardH: (height - y0 - 2 * g) / 3
    readonly property real cardW: (width - 2 * g) / 3

    Item {
        anchors.fill: parent
        visible: !page.isOpen
        Repeater {
            model: page.metrics
            Card {
                id: tile
                x: (index % 3) * (page.cardW + page.g); y: page.y0 + Math.floor(index / 3) * (page.cardH + page.g)
                width: page.cardW; height: page.cardH
                readonly property var vals: page.values(modelData.key)
                readonly property var now: page.last(vals)
                Text { x: 20; y: 14; text: Tr.t(modelData.title); color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                Text { anchors.right: parent.right; anchors.rightMargin: 20; y: 14; color: Tokens.dim
                       text: tileMouse.containsMouse ? Tr.t("Click to enlarge") : Tr.line(Tr.t("last ") + page.names[page.range])
                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                Text { x: 20; y: 34; color: Tokens.text; font.family: Tokens.font; font.pixelSize: 28; font.bold: true
                       text: page.valueText(modelData) }
                GraphChart {
                    visible: tile.now !== null
                    x: 16; y: 78; width: parent.width - 32; height: parent.height - 78 - 14
                    series: [tile.vals]; colors: [modelData.color]
                    maxValue: modelData.unit === "net" ? page.netMax : 100
                    fmtKind: modelData.unit === "net" ? "net" : ""
                    unit: modelData.unit === "°C" ? "°" : modelData.unit === "%" ? "%" : ""
                    slotMs: page.slotMs; scrollEnd: page.d.end_ms || 0; extra: page.d.extra || 0
                    delayMs: page.d.delay_ms || 0; nowMs: page.nowMs
                }
                Text { visible: tile.now === null; anchors.centerIn: parent; text: Tr.t("No sensor data"); color: Tokens.dim
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                Rectangle { anchors.fill: parent; radius: Tokens.radius; color: "transparent"
                            border.width: 1; border.color: Tokens.accent; visible: tileMouse.containsMouse }
                MouseArea { id: tileMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: page.open(modelData.key) }
            }
        }

        Card {
            x: 0; y: page.y0 + 2 * (page.cardH + page.g); width: page.width; height: page.cardH
            Text { x: 20; y: 14; text: Tr.t("Fan speed (RPM)"); color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            Row {
                x: 20; y: 38; spacing: 18; visible: page.fanNames.length > 0
                Repeater {
                    model: page.fanNames
                    Row {
                        spacing: 6
                        Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                                    color: page.fanColors[index % page.fanColors.length] }
                        Text { color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true
                               text: modelData + "  " + Math.round(page.last(page.fanSeries[index]) || 0) + Tr.t(" RPM") }
                    }
                }
            }
            GraphChart {
                visible: page.fanNames.length > 0
                x: 16; y: 66; width: parent.width - 32; height: parent.height - 66 - 14
                series: page.fanSeries; colors: page.fanColors; maxValue: page.fanMax; fill: page.fanNames.length === 1
                slotMs: page.slotMs; scrollEnd: page.d.end_ms || 0; extra: page.d.extra || 0
                delayMs: page.d.delay_ms || 0; nowMs: page.nowMs
            }
            Text { visible: page.fanNames.length === 0; anchors.centerIn: parent; width: parent.width - 60
                   horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: Tokens.dim
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                   text: Tr.t("No fan speed sensor was found. Fan RPM needs administrator rights, and some laptops do not expose their fans to software. The graph starts when you open this page.") }
            Rectangle { anchors.fill: parent; radius: Tokens.radius; color: "transparent"
                        border.width: 1; border.color: Tokens.accent; visible: fanMouse.containsMouse }
            MouseArea { id: fanMouse; anchors.fill: parent; enabled: page.fanNames.length > 0
                        hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: page.open("fan:" + page.fanNames[0]) }
        }
    }

    Card {
        id: large
        x: 0; y: page.y0; width: page.width; height: page.height - page.y0
        visible: opacity > 0
        opacity: page.isOpen ? 1 : 0
        scale: page.isOpen ? 1 : 0.98
        Behavior on opacity { NumberAnimation { duration: 140 } }
        Behavior on scale { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        Keys.onEscapePressed: page.close()

        Text { x: 20; y: 16; width: parent.width - 90; elide: Text.ElideRight; color: Tokens.text
               text: page.openItems.map(function (m) { return Tr.t(m.title) }).join("  +  ")
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.bold: true }
        Rectangle {
            id: closeBtn
            anchors.right: parent.right; anchors.rightMargin: 14; y: 12; width: 30; height: 30; radius: 9
            color: closeMouse.containsMouse ? Tokens.fg(0.12) : Tokens.fg(0.05)
            border.width: 1; border.color: Tokens.line
            Text { anchors.centerIn: parent; text: "✕"; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
            MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor; onClicked: page.close() }
        }
        Text { x: 20; y: 42; text: Tr.t("Click a name to add it to this graph or remove it"); color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        Flow {
            id: chips
            x: 20; y: 64; width: parent.width - 40; spacing: 8
            Repeater {
                model: page.allMetrics
                Rectangle {
                    readonly property bool on: page.openKeys.indexOf(modelData.key) >= 0
                    width: chipRow.width + 22; height: 32; radius: 9
                    color: on ? Tokens.fg(0.09) : chipMouse.containsMouse ? Tokens.fg(0.06) : Tokens.fg(0.03)
                    border.width: 1; border.color: on ? modelData.color : Tokens.line
                    Row {
                        id: chipRow; anchors.centerIn: parent; spacing: 7
                        Rectangle { width: 10; height: 10; radius: 5; anchors.verticalCenter: parent.verticalCenter
                                    color: parent.parent.on ? modelData.color : Tokens.dim }
                        Text { text: Tr.t(modelData.title); color: parent.parent.on ? Tokens.text : Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: parent.parent.on }
                        Text { text: page.valueText(modelData); color: parent.parent.on ? Tokens.text : Tokens.dim
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    }
                    MouseArea { id: chipMouse; anchors.fill: parent; hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor; onClicked: page.toggle(modelData.key) }
                }
            }
        }
        GraphChart {
            id: largeChart
            visible: page.isOpen
            x: 16; y: chips.y + chips.height + 16; width: parent.width - 32
            height: parent.height - y - 16
            series: page.openSeries
            colors: page.openItems.map(function (m) { return m.color })
            fill: page.openItems.length === 1
            maxValue: page.maxOf(page.mainKind)
            fmtKind: page.mainKind === "pct" ? "" : page.mainKind
            unit: page.openUnit
            rightMax: page.sideKind !== "" ? page.maxOf(page.sideKind) : 0
            rightKind: page.sideKind
            slotMs: page.slotMs; scrollEnd: page.d.end_ms || 0; extra: page.d.extra || 0
            delayMs: page.d.delay_ms || 0; nowMs: page.nowMs
        }
    }
}
