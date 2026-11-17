import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

// Home: four cards (CPU, GPU, memory, storage), the performance chart, what is going on
// right now, the network and this PC. Every number comes from backend.dashboard (real
// readings); missing data shows "--" - never a made-up number.
Item {
    id: page
    readonly property var d: backend.dashboard
    readonly property bool ready: d && d.ready === true
    readonly property var cards: ready && d.cards ? d.cards : ({})
    readonly property var cpuC: cards.cpu || ({})
    readonly property var gpuC: cards.gpu || ({})
    readonly property var ramC: cards.ram || ({})
    readonly property var diskC: cards.disk || ({})
    readonly property var net: ready && d.network ? d.network : ({})
    readonly property var pc: ready && d.pc_info ? d.pc_info : ({})
    readonly property var now: ready && d.now ? d.now : ({})
    readonly property var safe: ready && d.safe ? d.safe : ({active: false})
    readonly property int g: Tokens.gap

    // the chart: real time (4 readings a second) or 1 minute
    readonly property var spans: [0, 60]
    property var pd: backend.graphs(spans[backend.rangeIndex])
    function refreshChart() { pd = backend.graphs(spans[backend.rangeIndex]) }
    Connections { target: backend
                  function onDashboardChanged() { if (backend.rangeIndex !== 0) page.refreshChart() }
                  function onHudChanged() { if (backend.rangeIndex === 0) page.refreshChart() }
                  function onRangeChanged() { backend.setGraphFast(backend.rangeIndex === 0); page.refreshChart() } }
    Component.onCompleted: backend.setGraphFast(backend.rangeIndex === 0)

    function num(v, digits) { return v === null || v === undefined ? "--" : (digits ? v.toFixed(digits) : String(Math.round(v))) }
    function ghz(mhz) { return mhz ? (mhz / 1000).toFixed(1) + Tr.t(" GHz") : "" }
    function join(parts) { return parts.filter(function (x) { return x !== "" }).join("  ·  ") }
    function go(name) { Window.window.goTo(name) }

    PageHeader {
        id: head
        width: parent.width
        kicker: ready ? Tr.line(Tr.t("Welcome back") + (d.user ? ", " + d.user : "") + (d.pc ? "  ·  " + d.pc : "")) : ""
        title: Tr.t("Home")
        Rectangle {
            width: ovRow.width + 28; height: 40; radius: 10; color: Tokens.card
            border.width: 1; border.color: Tokens.line
            Row { id: ovRow; anchors.centerIn: parent; spacing: 14
                  Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Overlay"); color: Tokens.text
                         font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.weight: Font.DemiBold }
                  ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: backend.settings.on
                                 onToggled: function (v) { backend.setSetting("on", v) } } }
        }
        Rectangle {
            width: hudRow.width + 28; height: 40; radius: 10; color: Tokens.card
            border.width: 1; border.color: Tokens.line
            Row { id: hudRow; anchors.centerIn: parent; spacing: 14
                  Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Graph overlay"); color: Tokens.text
                         font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.weight: Font.DemiBold }
                  ToggleSwitch { anchors.verticalCenter: parent.verticalCenter
                                 checked: (backend.hudStyles[0] || ({})).hud_on === true
                                 onToggled: function (v) { backend.setHudSetting(0, "hud_on", v) } } }
        }
    }

    // ---- the four cards
    readonly property real y0: head.height + 12
    readonly property real tileW: (width - 3 * g) / 4
    readonly property real tileH: 168
    MetricTile {
        x: 0; y: page.y0; width: page.tileW; height: page.tileH
        title: "CPU"; caption: Tr.t("Processor"); glyph: ""; tone: Tokens.cpu
        status: page.cpuC.status || "none"
        big: page.num(page.cpuC.use); bigUnit: "%"
        line1: page.join([Tr.t("Usage"), (page.cpuC.approx ? "~" : "") + page.ghz(page.cpuC.clock_mhz),
                          page.cpuC.power_w !== null && page.cpuC.power_w !== undefined ? Math.round(page.cpuC.power_w) + " W" : ""])
        line2: page.cpuC.name || ""
        warning: page.cpuC.note || ""
        gauge: true; gaugeValue: page.cpuC.temp !== undefined ? page.cpuC.temp : null
    }
    MetricTile {
        x: page.tileW + page.g; y: page.y0; width: page.tileW; height: page.tileH
        title: "GPU"; caption: Tr.t("Graphics"); glyph: ""; tone: Tokens.gpu
        status: page.gpuC.status || "none"
        big: page.num(page.gpuC.use); bigUnit: "%"
        line1: page.join([Tr.t("Usage"), page.ghz(page.gpuC.clock_mhz),
                          page.gpuC.power_w !== null && page.gpuC.power_w !== undefined ? Math.round(page.gpuC.power_w) + " W" : ""])
        line2: page.gpuC.name || ""
        gauge: true; gaugeValue: page.gpuC.temp !== undefined ? page.gpuC.temp : null
    }
    MetricTile {
        x: 2 * (page.tileW + page.g); y: page.y0; width: page.tileW; height: page.tileH
        title: Tr.t("Memory"); caption: page.ramC.total_gb !== undefined ? Math.round(page.ramC.total_gb) + " GB" : ""
        glyph: ""; tone: Tokens.ram
        status: page.ramC.status || "none"
        big: page.num(page.ramC.use); bigUnit: "%"
        line1: page.ramC.used_gb !== undefined ? page.ramC.used_gb.toFixed(1) + Tr.t(" GB used of ") + Math.round(page.ramC.total_gb) + " GB" : ""
        bar: page.ramC.use !== null && page.ramC.use !== undefined ? page.ramC.use / 100 : -1
    }
    MetricTile {
        x: 3 * (page.tileW + page.g); y: page.y0; width: page.tileW; height: page.tileH
        title: Tr.t("Storage"); caption: page.diskC.mount ? Tr.t("Drive ") + page.diskC.mount : ""
        glyph: ""; tone: Tokens.disk
        status: page.diskC.status || "none"
        big: page.num(page.diskC.free_gb); bigUnit: " GB"
        line1: page.diskC.total_gb !== undefined ? Tr.t("free of ") + Math.round(page.diskC.total_gb) + " GB" : ""
        bar: page.diskC.use !== null && page.diskC.use !== undefined ? page.diskC.use / 100 : -1
    }

    // ---- lower part: chart + network (left), right now + this PC (right)
    readonly property real y1: y0 + tileH + g
    readonly property real leftW: Math.round((width - g) * 0.635)
    readonly property real rightW: width - leftW - g
    readonly property real netH: 148
    readonly property real perfH: height - y1 - netH - g

    Card {                                          // ---- performance
        x: 0; y: page.y1; width: page.leftW; height: page.perfH
        Text { x: 20; y: 16; text: Tr.t("Performance"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
        Row {
            x: 20; y: 42; spacing: 16
            Repeater {
                model: 3
                Row {
                    spacing: 6
                    readonly property var c: [page.cpuC, page.ramC, page.gpuC][index]
                    Rectangle { width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                color: [Tokens.cpu, Tokens.ram, Tokens.gpu][index] }
                    Text { text: ["CPU", "RAM", "GPU"][index] + " " + page.num(parent.c.use) + "%"; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: 12 }
                }
            }
        }
        Segmented { anchors.right: parent.right; anchors.rightMargin: 18; y: 16; width: 190
                    model: backend.rangeNames; index: backend.rangeIndex
                    onPicked: function (i) { backend.setRange(i) } }
        GraphChart {
            x: 14; y: 72; width: parent.width - 30; height: parent.height - 72 - 16
            series: [page.pd.c_use || [], page.pd.r_use || [], page.pd.g_use || []]
            colors: [Tokens.cpu, Tokens.ram, Tokens.gpu]; fill: false; maxValue: 100; unit: "%"
            slots: page.pd.points || 60; slotMs: page.pd.slot_ms || 1000
            scrollEnd: page.pd.end_ms || 0; extra: page.pd.extra || 0
            delayMs: page.pd.delay_ms || 0; nowMs: Clock.now
        }
    }

    Card {                                          // ---- network
        x: 0; y: page.y1 + page.perfH + page.g; width: page.leftW; height: page.netH
        Rectangle { x: 20; y: 16; width: 34; height: 34; radius: 9; color: Tokens.tint(Tokens.cyan, 0.14)
                    Text { anchors.centerIn: parent; text: ""; color: Tokens.cyan
                           font.family: Tokens.iconFont; font.pixelSize: 17 } }
        Column {
            x: 64; y: 17; spacing: 1
            Text { text: Tr.t("Network"); color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: 14; font.weight: Font.DemiBold }
            Text { text: page.net.adapter ? Tr.line(page.net.adapter + (page.net.link ? "  ·  " + page.net.link + " Mbit/s" : ""))
                                          : Tr.t("Not connected")
                   color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 12 }
        }
        Pill { anchors.right: parent.right; anchors.rightMargin: 18; y: 16; height: 32
               label: Tr.t("Usage history"); onClicked: page.go("Network usage") }
        Row {
            x: 20; y: 72; spacing: 30
            Repeater {
                model: 3
                Column {
                    spacing: 2
                    Text { text: [Tr.t("Download"), Tr.t("Upload"), Tr.t("Since start-up")][index]; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 12 }
                    Text { text: [page.net.down || "--", page.net.up || "--", page.net.since_boot || "--"][index]
                           color: [Tokens.cyan, Tokens.violet, Tokens.text][index]
                           font.family: Tokens.fontDisplay; font.pixelSize: 22; font.weight: Font.DemiBold }
                }
            }
        }
        Sparkline {
            anchors.right: parent.right; anchors.rightMargin: 18; y: 74; width: parent.width * 0.42; height: 54
            values: page.net.hist || []
            maxValue: { var m = 1; var h = values || []; for (var i = 0; i < h.length; ++i) if (h[i] > m) m = h[i]; return m * 1.15 }
            color: Tokens.cyan; fill: false
        }
    }

    Card {                                          // ---- right now
        id: nowCard
        x: page.leftW + page.g; y: page.y1; width: page.rightW; height: page.perfH
        Text { x: 20; y: 16; text: Tr.t("Right now"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
        Rectangle {
            visible: !!page.now.game
            anchors.right: parent.right; anchors.rightMargin: 18; y: 16
            width: gameRow.width + 16; height: 22; radius: 6; color: Tokens.accentA(0.13)
            Row { id: gameRow; anchors.centerIn: parent; spacing: 6
                  Rectangle { width: 7; height: 7; radius: 4; color: Tokens.accent; anchors.verticalCenter: parent.verticalCenter }
                  Text { text: Tr.t("Game in front"); color: Tokens.accent
                         font.family: Tokens.font; font.pixelSize: 12; font.weight: Font.DemiBold } }
        }
        FitBar { x: 18; y: 50; width: parent.width - 36; height: 46
                 model: backend.overlay.groups.length > 0 ? backend.overlay : backend.preview
                 style: backend.settings }
        readonly property var facts: [
            {t: "Game", on: !!page.now.game, v: page.now.game ? page.now.game.name : Tr.t("No game in front")},
            {t: "Frame rate", on: !!page.now.game,
             v: page.now.game ? Tr.line(page.now.game.fps + " FPS" + (page.now.game.low ? "  ·  1% low " + page.now.game.low : "")) : "--"},
            {t: "Session", on: page.now.recording === true,
             v: page.now.recording ? Tr.t("Recording") : Tr.t(page.now.session || "")},
            {t: "Last session", on: false,
             v: page.now.last ? Tr.line(page.now.last.game + (page.now.last.avg_fps ? "  ·  " + Math.round(page.now.last.avg_fps) + " FPS" : "")) : Tr.t("none yet")},
            {t: "Anti-cheat safe mode", on: page.safe.active === true,
             v: page.safe.active ? Tr.line(Tr.t("Active now") + (page.safe.game ? "  ·  " + page.safe.game : "")) : Tr.t("Not active now")}
        ]
        Column {
            x: 20; y: 108; width: parent.width - 40
            Repeater {
                model: 5                    // fixed rows: only their texts change each second
                Item {
                    id: fact
                    readonly property var f: nowCard.facts[index] || ({})
                    width: parent.width; height: 36
                    Rectangle { visible: index > 0; width: parent.width; height: 1; color: Tokens.line }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t(fact.f.t || ""); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                           width: parent.width - 150; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                           text: fact.f.v || ""; color: fact.f.on ? Tokens.text : Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                           font.weight: fact.f.on === true ? Font.DemiBold : Font.Normal }
                }
            }
        }
    }

    Card {                                          // ---- this PC
        id: pcCard
        x: page.leftW + page.g; y: page.y1 + page.perfH + page.g; width: page.rightW; height: page.netH
        Text { x: 20; y: 16; text: Tr.t("This PC"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
        Text { anchors.right: parent.right; anchors.rightMargin: 20; y: 19; width: parent.width - 140
               horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
               text: page.pc.windows || ""; color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 12 }
        readonly property var items: [
            {t: "Up time", v: page.pc.uptime || "--", c: Tokens.text},
            {t: "Battery", v: page.pc.battery ? Tr.line(page.pc.battery.pct + "%  ·  " + Tr.t(page.pc.battery.plugged ? "plugged in" : "on battery"))
                                             : Tr.t("No battery"), c: Tokens.text},
            {t: "Power plan", v: page.pc.plan || "--", c: Tokens.text},
            {t: "PC check", v: page.pc.score !== null && page.pc.score !== undefined ? page.pc.score + " / 100" : Tr.t("Not scanned yet"),
             c: page.pc.score !== null && page.pc.score !== undefined ? (page.pc.score >= 80 ? Tokens.accent : page.pc.score >= 60 ? Tokens.warn : Tokens.danger) : Tokens.dim,
             link: true}
        ]
        Grid {
            x: 20; y: 50; columns: 2; columnSpacing: 16; rowSpacing: 12
            Repeater {
                model: 4
                Column {
                    id: pcItem
                    readonly property var it: pcCard.items[index] || ({})
                    width: (pcCard.width - 56) / 2; spacing: 1
                    Text { text: Tr.t(pcItem.it.t || ""); color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 12 }
                    Text { text: pcItem.it.v || ""; color: pcItem.it.c || Tokens.text; width: pcItem.width; elide: Text.ElideRight
                           font.family: Tokens.font; font.pixelSize: 14; font.weight: Font.DemiBold
                           MouseArea { anchors.fill: parent; enabled: pcItem.it.link === true
                                       cursorShape: Qt.PointingHandCursor; onClicked: page.go("PC check") } }
                }
            }
        }
    }
}
