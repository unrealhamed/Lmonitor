import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

// Home: welcome card, four hardware cards, network, performance chart and the
// overlay controls. Every number comes from backend.dashboard (real readings);
// missing data shows "--" or "No data".
Item {
    id: page
    readonly property var d: backend.dashboard
    readonly property bool ready: d && d.ready === true
    readonly property var cards: ready && d.cards ? d.cards : ({})
    readonly property var cpuC: cards.cpu || ({})
    readonly property var gpuC: cards.gpu || ({})
    readonly property var ramC: cards.ram || ({})
    readonly property var diskC: cards.disk || ({})
    readonly property var st: ready && d.status ? d.status : ({})
    readonly property var s: backend.settings
    readonly property int g: Tokens.gap

    function ghz(mhz) { return mhz ? (mhz / 1000).toFixed(1) + " GHz" : "" }
    function go(name) { Window.window.goTo(name) }
    function worst(a, b) {
        var rank = {none: 0, ok: 1, low: 2, warm: 2, high: 3, hot: 3, full: 3}
        return (rank[a] || 0) >= (rank[b] || 0) ? a : b
    }
    readonly property string tempStatus: {
        var a = cpuC.temp !== null && cpuC.temp !== undefined ? cpuC.status : "none"
        var b = gpuC.temp !== null && gpuC.temp !== undefined ? gpuC.status : "none"
        return worst(a, b)
    }
    function tempLine() {
        if (!ready) return ""
        var p = []
        if (cpuC.temp !== null && cpuC.temp !== undefined) p.push("CPU " + Math.round(cpuC.temp) + "°")
        if (gpuC.temp !== null && gpuC.temp !== undefined) p.push("GPU " + Math.round(gpuC.temp) + "°")
        return p.length ? p.join(" · ") : "No temperature sensor"
    }

    PageHeader {
        id: head
        width: parent.width
        kicker: ready && d.pc ? d.pc : "This PC"
        title: "Home"
        Rectangle {
            width: 168; height: 42; radius: 12
            color: Tokens.fg(0.05); border.width: 1; border.color: Tokens.line
            Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: "Overlay"
                   color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            ToggleSwitch { anchors.right: parent.right; anchors.rightMargin: 10
                           anchors.verticalCenter: parent.verticalCenter
                           checked: page.s.on
                           onToggled: function (v) { backend.setSetting("on", v) } }
        }
    }

    readonly property real bodyY: head.height + 12
    readonly property real rowA: 344
    readonly property real rowB: height - bodyY - rowA - g
    readonly property real leftW: Math.round(width * 0.38)
    readonly property real rightW: width - leftW - g

    // ---- welcome
    Card {
        x: 0; y: page.bodyY; width: page.leftW; height: page.rowA; tint: true
        Text { x: 22; y: 20; text: "Welcome back"; color: Tokens.sub
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Text { x: 22; y: 40; width: parent.width - 44; elide: Text.ElideRight
               text: page.ready && page.d.user ? page.d.user : "Gamer"
               color: Tokens.text; font.family: Tokens.font; font.pixelSize: 34; font.bold: true }
        Column {
            x: 22; y: 100; spacing: 12
            Repeater {
                model: [
                    {t: "Temperatures", s: page.tempStatus, sub: page.tempLine()},
                    {t: "Memory", s: page.ready ? page.ramC.status || "none" : "none",
                     sub: page.ready && page.ramC.used_gb !== undefined ? page.ramC.used_gb.toFixed(1) + " of " + Math.round(page.ramC.total_gb) + " GB used" : ""},
                    {t: "Storage", s: page.ready ? page.diskC.status || "none" : "none",
                     sub: page.ready && page.diskC.free_gb !== undefined ? Math.round(page.diskC.free_gb) + " GB free on " + page.diskC.mount : "No drive data"},
                    {t: "FPS capture", s: page.ready ? (({ready: "ok", missing: "warm", idle: "none"})[page.st.fps] || "none") : "none",
                     sub: page.ready ? (({ready: "Ready", missing: "Capture tool missing", idle: "Starts with a game"})[page.st.fps] || "") : ""}
                ]
                Row {
                    spacing: 12
                    Dot { y: 6; status: modelData.s }
                    Column {
                        Text { text: modelData.t || ""; color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: 15; font.bold: true }
                        Text { text: modelData.sub || ""; color: Tokens.dim
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    }
                }
            }
        }
        Row {
            x: 22; y: parent.height - 56; spacing: 10
            Pill { label: "Performance"; onClicked: page.go("Performance") }
            Pill { label: "Hardware"; onClicked: page.go("Hardware") }
        }
    }

    // ---- hardware cards
    readonly property real rx: leftW + g
    readonly property real hh: (rowA - g) / 2
    readonly property real w1: Math.round(rightW * 0.5)
    readonly property real w2: Math.round((rightW - w1 - 2 * g) / 2)

    HwCard {
        x: page.rx; y: page.bodyY; width: page.w1; height: page.hh
        title: "CPU"; ring: true; ringColor: Tokens.cpu
        model: page.cpuC.name || ""
        info: page.cpuC || ({})
        detail: page.ready ? (page.cpuC.approx ? "~" : "") + page.ghz(page.cpuC.clock_mhz) : ""
    }
    HwCard {
        x: page.rx + page.w1 + page.g; y: page.bodyY; width: page.w2; height: page.hh
        title: "RAM"
        model: page.ready && page.ramC.total_gb !== undefined ? Math.round(page.ramC.total_gb) + " GB" : ""
        info: page.ramC || ({})
        detail: page.ready && page.ramC.used_gb !== undefined ? page.ramC.used_gb.toFixed(1) + " GB used" : ""
    }
    HwCard {
        x: page.rx + page.w1 + page.w2 + 2 * page.g; y: page.bodyY; width: page.w2; height: page.hh
        title: "Storage"
        model: page.ready && page.diskC.mount ? "Drive " + page.diskC.mount : ""
        info: page.diskC || ({})
        detail: page.ready && page.diskC.free_gb !== undefined ? Math.round(page.diskC.free_gb) + " GB free" : ""
    }
    HwCard {
        x: page.rx; y: page.bodyY + page.hh + page.g; width: page.w1; height: page.hh
        title: "GPU"; ring: true; ringColor: Tokens.gpu
        model: page.gpuC.name || ""
        info: page.gpuC || ({})
        detail: page.ready ? ((page.gpuC.power_w !== null && page.gpuC.power_w !== undefined ? Math.round(page.gpuC.power_w) + " W · " : "") + page.ghz(page.gpuC.clock_mhz)) : ""
    }
    Card {
        x: page.rx + page.w1 + page.g; y: page.bodyY + page.hh + page.g
        width: page.rightW - page.w1 - page.g; height: page.hh
        Text { x: 18; y: 16; text: "Network"; color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 18; font.bold: true }
        Text { anchors.right: parent.right; anchors.rightMargin: 18; y: 20
               text: "↓ " + (page.ready ? page.d.network.down : "--") + "   ↑ " + (page.ready ? page.d.network.up : "--")
               color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        Sparkline {
            x: 10; y: 50; width: parent.width - 20; height: parent.height - 60
            values: page.ready ? page.d.network.hist : []
            maxValue: { var m = 1; var h = values || []; for (var i = 0; i < h.length; ++i) if (h[i] > m) m = h[i]; return m * 1.15 }
            color: Tokens.violet
        }
    }

    // ---- chart + overlay controls
    PerfChart {
        x: 0; y: page.bodyY + page.rowA + page.g
        width: Math.round(page.width * 0.58) - page.g / 2; height: page.rowB
        series: page.ready ? page.d.perf : [[], [], []]
        rangeIndex: backend.rangeIndex
        rangeNames: backend.rangeNames
        onRangePicked: function (i) { backend.setRange(i) }
    }
    Card {
        x: Math.round(page.width * 0.58) + page.g / 2; y: page.bodyY + page.rowA + page.g
        width: page.width - x; height: page.rowB
        Text { x: 20; y: 16; text: "Overlay"; color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 18; font.bold: true }
        FitBar { x: 16; y: 50; width: parent.width - 32; height: 54
                 model: backend.overlay.groups.length > 0 ? backend.overlay : backend.preview
                 style: backend.settings }
        Column {
            x: 20; y: 120; width: parent.width - 40; spacing: 12
            Repeater {
                model: [
                    {t: "Show the overlay in games", k: "on", on: page.s.on, yes: true, no: false},
                    {t: "Show only when I press F9", k: "show_mode", on: page.s.show_mode === "hotkey", yes: "hotkey", no: "always"},
                    {t: "Liquid glass look", k: "look", on: page.s.look === "glass", yes: "glass", no: "dark"}
                ]
                Item {
                    width: parent.width; height: 28
                    Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.t || ""; color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    ToggleSwitch { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                   checked: modelData.on
                                   onToggled: function (v) { backend.setSetting(modelData.k, v ? modelData.yes : modelData.no) } }
                }
            }
        }
        Pill { x: 20; y: parent.height - 56; width: parent.width - 40; label: "All overlay settings  ›"
               onClicked: page.go("Overlay") }
    }
}
