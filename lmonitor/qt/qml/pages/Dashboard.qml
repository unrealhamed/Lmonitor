import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

// Home: welcome card, four hardware cards, network, performance chart and what is
// going on right now (game, frame rate, session). Every number comes from backend.dashboard (real readings);
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
    readonly property var now: ready && d.now ? d.now : ({})
    readonly property var safe: ready && d.safe ? d.safe : ({active: false})

    // the chart: real time (4 readings a second) or 1 minute
    readonly property var spans: [0, 60]
    property var pd: backend.graphs(spans[backend.rangeIndex])
    function refreshChart() { pd = backend.graphs(spans[backend.rangeIndex]) }
    Connections { target: backend
                  function onDashboardChanged() { if (backend.rangeIndex !== 0) page.refreshChart() }
                  function onHudChanged() { if (backend.rangeIndex === 0) page.refreshChart() }
                  function onRangeChanged() { backend.setGraphFast(backend.rangeIndex === 0); page.refreshChart() } }
    Component.onCompleted: backend.setGraphFast(backend.rangeIndex === 0)

    function ghz(mhz) { return mhz ? (mhz / 1000).toFixed(1) + Tr.t(" GHz") : "" }
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
        if (cpuC.temp !== null && cpuC.temp !== undefined) p.push(Tr.t("CPU ") + Math.round(cpuC.temp) + "°")
        if (gpuC.temp !== null && gpuC.temp !== undefined) p.push(Tr.t("GPU ") + Math.round(gpuC.temp) + "°")
        return p.length ? p.join(" · ") : Tr.t("No temperature sensor")
    }

    PageHeader {
        id: head
        width: parent.width
        kicker: ready && d.pc ? d.pc : Tr.t("This PC")
        title: Tr.t("Home")
        Rectangle {
            width: 168; height: 42; radius: 12
            color: Tokens.fg(0.05); border.width: 1; border.color: Tokens.line
            Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Overlay")
                   color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            ToggleSwitch { anchors.right: parent.right; anchors.rightMargin: 10
                           anchors.verticalCenter: parent.verticalCenter
                           checked: page.s.on
                           onToggled: function (v) { backend.setSetting("on", v) } }
        }
        Rectangle {
            width: gl.width + 86; height: 42; radius: 12
            color: Tokens.fg(0.05); border.width: 1; border.color: Tokens.line
            Text { id: gl; x: 16; anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Graph overlay")
                   color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            ToggleSwitch { anchors.right: parent.right; anchors.rightMargin: 10
                           anchors.verticalCenter: parent.verticalCenter
                           checked: (backend.hudStyles[0] || ({})).hud_on === true
                           onToggled: function (v) { backend.setHudSetting(0, "hud_on", v) } }
        }
    }

    readonly property real bodyY: head.height + 12
    readonly property real rowA: 344
    readonly property real rowB: height - bodyY - rowA - g
    readonly property real leftW: Math.round(width * 0.38)
    readonly property real rightW: width - leftW - g

    // ---- welcome
    Card {
        id: welcome
        x: 0; y: page.bodyY; width: page.leftW; height: page.rowA; tint: true
        Text { x: 22; y: 20; text: Tr.t("Welcome back"); color: Tokens.sub
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Text { x: 22; y: 40; width: parent.width - 44; elide: Text.ElideRight
               text: page.ready && page.d.user ? page.d.user : Tr.t("Gamer")
               color: Tokens.text; font.family: Tokens.font; font.pixelSize: 34; font.bold: true }
        // The rows stay; only their texts change each second (a list made anew every second
        // made the Repeater delete and build all its rows again).
        readonly property var checks: [
                    {t: Tr.t("Temperatures"), s: page.tempStatus, sub: page.tempLine()},
                    {t: Tr.t("Memory"), s: page.ready ? page.ramC.status || "none" : "none",
                     sub: page.ready && page.ramC.used_gb !== undefined ? page.ramC.used_gb.toFixed(1) + Tr.t(" of ") + Math.round(page.ramC.total_gb) + Tr.t(" GB used") : ""},
                    {t: Tr.t("Storage"), s: page.ready ? page.diskC.status || "none" : "none",
                     sub: page.ready && page.diskC.free_gb !== undefined ? Math.round(page.diskC.free_gb) + Tr.t(" GB free on ") + page.diskC.mount : Tr.t("No drive data")},
                    {t: Tr.t("FPS capture"), s: page.ready ? (({ready: "ok", missing: "warm", idle: "none"})[page.st.fps] || "none") : "none",
                     sub: page.ready ? (({ready: Tr.t("Ready"), missing: Tr.t("Capture tool missing"), idle: Tr.t("Starts with a game")})[page.st.fps] || "") : ""}
                ]
        Column {
            x: 22; y: 100; spacing: 12
            Repeater {
                model: 4
                Row {
                    id: checkRow
                    readonly property var c: welcome.checks[index] || ({})
                    spacing: 12
                    Dot { y: 6; status: checkRow.c.s || "none" }
                    Column {
                        Text { text: checkRow.c.t || ""; color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: 15; font.bold: true }
                        Text { text: Tr.t(checkRow.c.sub || ""); color: Tokens.dim
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    }
                }
            }
        }
        Row {
            x: 22; y: parent.height - 56; spacing: 10
            Pill { label: Tr.t("Graphs"); onClicked: page.go("Graphs") }
            Pill { label: Tr.t("Hardware"); onClicked: page.go("Hardware") }
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
        detail: page.ready && page.ramC.used_gb !== undefined ? page.ramC.used_gb.toFixed(1) + Tr.t(" GB used") : ""
    }
    HwCard {
        x: page.rx + page.w1 + page.w2 + 2 * page.g; y: page.bodyY; width: page.w2; height: page.hh
        title: Tr.t("Storage")
        model: page.ready && page.diskC.mount ? Tr.t("Drive ") + page.diskC.mount : ""
        info: page.diskC || ({})
        detail: page.ready && page.diskC.free_gb !== undefined ? Math.round(page.diskC.free_gb) + Tr.t(" GB free") : ""
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
        Text { x: 18; y: 16; text: Tr.t("Network"); color: Tokens.text
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

    // ---- chart + what is going on right now
    PerfChart {
        x: 0; y: page.bodyY + page.rowA + page.g
        width: Math.round(page.width * 0.58) - page.g / 2; height: page.rowB
        d: page.pd; nowMs: Clock.now
        rangeIndex: backend.rangeIndex
        rangeNames: backend.rangeNames
        onRangePicked: function (i) { backend.setRange(i) }
    }
    Card {
        id: nowCard
        x: Math.round(page.width * 0.58) + page.g / 2; y: page.bodyY + page.rowA + page.g
        width: page.width - x; height: page.rowB
        Text { x: 20; y: 16; text: Tr.t("Right now"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 18; font.bold: true }
        FitBar { x: 16; y: 50; width: parent.width - 32; height: 54
                 model: backend.overlay.groups.length > 0 ? backend.overlay : backend.preview
                 style: backend.settings }
        readonly property var facts: [
                    {t: "Game", on: !!page.now.game,
                     v: page.now.game ? page.now.game.name : Tr.t("No game in front")},
                    {t: "Frame rate", on: !!page.now.game,
                     v: page.now.game ? Tr.line(page.now.game.fps + " FPS  ·  " + Tr.t("avg ") + page.now.game.avg
                                                + (page.now.game.low ? "  ·  1% low " + page.now.game.low : "")) : "--"},
                    {t: "Session", on: page.now.recording === true,
                     v: page.now.recording ? Tr.t("Recording") : Tr.t(page.now.session || "")},
                    {t: "Last session", on: false,
                     v: page.now.last ? Tr.line(page.now.last.game + (page.now.last.avg_fps ? "  ·  " + Math.round(page.now.last.avg_fps) + " FPS" : "")
                                                + "  ·  " + page.now.last.when) : Tr.t("none yet")},
                    {t: "Anti-cheat safe mode", on: page.safe.active === true,
                     v: page.safe.active ? Tr.line(Tr.t("Active now") + (page.safe.game ? "  ·  " + page.safe.game : "")) : Tr.t("Not active now")}
                ]
        Column {
            x: 20; y: 118; width: parent.width - 40; spacing: 9
            Repeater {
                model: 5                    // fixed rows: only their texts change each second
                Item {
                    id: fact
                    readonly property var f: nowCard.facts[index] || ({})
                    width: parent.width; height: 22
                    Rectangle { y: 7; width: 8; height: 8; radius: 4; color: fact.f.on ? Tokens.accent : Tokens.dim }
                    Text { x: 18; anchors.verticalCenter: parent.verticalCenter; text: Tr.t(fact.f.t || ""); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                           width: parent.width - 170; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                           text: fact.f.v || ""; color: fact.f.on ? Tokens.text : Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: fact.f.on === true }
                }
            }
        }
        Row {
            x: 20; y: parent.height - 56; spacing: 10
            Pill { label: Tr.t("Sessions"); onClicked: page.go("Sessions") }
            Pill { label: Tr.t("Overlay"); onClicked: page.go("Overlay") }
            Pill { label: Tr.t("Graph overlay"); onClicked: page.go("Graph overlay") }
        }
    }
}
