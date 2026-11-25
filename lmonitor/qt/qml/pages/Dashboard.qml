import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

// Home. Left: a welcome card with the state of the PC in four lines and Smart Insights (the few
// most important findings, each with its reason). Right: processor, memory, storage, graphics
// card and network. Bottom: the performance chart, what is going on right now, and this PC.
// Every number comes from backend.dashboard (real readings); missing data shows "--".
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
    readonly property var ins: ready && d.insights ? d.insights : ({items: [], status: []})
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
    function sevColor(s) { return s === "warn" ? Tokens.danger : s === "notice" ? Tokens.warn : s === "info" ? Tokens.info
                                  : s === "ok" ? Tokens.accent : Tokens.dim }

    // ---- header: the three quick switches, the same settings as on their own pages
    component QuickSwitch: Rectangle {
        id: qs
        property string label: ""
        property bool on: false
        signal toggled(bool v)
        width: qsRow.width + 26; height: 40; radius: 10; color: Tokens.card
        border.width: 1; border.color: qs.on ? Tokens.accentA(0.45) : Tokens.line
        Row { id: qsRow; anchors.centerIn: parent; spacing: 12
              Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t(qs.label); color: Tokens.text
                     font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.weight: Font.DemiBold }
              ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: qs.on
                             onToggled: function (v) { qs.toggled(v) } } }
    }
    PageHeader {
        id: head
        width: parent.width
        kicker: ready && d.pc ? d.pc : ""
        title: Tr.t("Home")
        QuickSwitch { label: "Overlay"; on: backend.settings.on === true
                      onToggled: function (v) { backend.setSetting("on", v) } }
        QuickSwitch { label: "Graph overlay"; on: (backend.hudStyles[0] || ({})).hud_on === true
                      onToggled: function (v) { backend.setHudSetting(0, "hud_on", v) } }
        QuickSwitch { label: "Start with Windows"; on: backend.autostart === true
                      onToggled: function (v) { backend.setAutostart(v) } }
    }

    // ---- layout
    readonly property real y0: head.height + 12
    readonly property real tileH: 158
    readonly property real leftW: Math.round((width - 2 * g) * 0.31)
    readonly property real rx: leftW + g                         // the right part
    readonly property real rw: width - rx
    readonly property real bigW: Math.round((rw - 2 * g) * 0.40)  // CPU / GPU
    readonly property real smallW: (rw - bigW - 2 * g) / 2         // memory / storage
    readonly property real y1: y0 + 2 * tileH + 2 * g              // the bottom row
    readonly property real botH: height - y1
    readonly property real perfW: Math.round((width - 2 * g) * 0.46)
    readonly property real nowW: Math.round((width - 2 * g) * 0.31)
    readonly property real pcW: width - perfW - nowW - 2 * g

    Card {                                          // ---- welcome + state + Smart Insights
        id: insCard
        x: 0; y: page.y0; width: page.leftW; height: 2 * page.tileH + page.g
        clip: true
        Column {
            x: 20; y: 16; width: parent.width - 40; spacing: 0
            Text { text: Tr.t("Welcome back"); color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
            Text { width: parent.width; elide: Text.ElideRight; text: page.ready ? (page.d.user || "") : ""; color: Tokens.text
                   font.family: Tokens.fontDisplay; font.pixelSize: 26; font.weight: Font.DemiBold }
            Item { width: 1; height: 10 }
            Repeater {                              // temperatures, PC check, stability, graphics driver
                model: page.ins.status || []
                Item {
                    width: parent.width; height: 28
                    Rectangle { width: 7; height: 7; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                color: page.sevColor(modelData.sev) }
                    Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: Tr.t(modelData.t); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                           width: parent.width * 0.55; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                           text: Tr.t(modelData.v); color: modelData.link ? Tokens.accent : Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.weight: Font.DemiBold }
                    MouseArea { anchors.fill: parent; enabled: !!modelData.link; cursorShape: Qt.PointingHandCursor
                                onClicked: page.go(modelData.link) }
                }
            }
            Item { width: 1; height: 10 }
            Rectangle { width: parent.width; height: 1; color: Tokens.line }
            Item { width: 1; height: 10 }
            Row { spacing: 8
                  Text { text: ""; color: Tokens.accent; font.family: Tokens.iconFont; font.pixelSize: 14
                         anchors.verticalCenter: parent.verticalCenter }
                  Text { text: Tr.t("Smart insights"); color: Tokens.text; font.family: Tokens.font
                         font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold } }
            Item { width: 1; height: 6 }
            Repeater {
                model: (page.ins.items || []).slice(0, 3)
                Item {
                    id: insItem
                    property bool open: false
                    width: parent.width; height: insCol.height + 8
                    Rectangle { y: 6; width: 7; height: 7; radius: 4; color: page.sevColor(modelData.sev) }
                    Column {
                        id: insCol; x: 16; width: parent.width - 16; spacing: 2
                        Text { width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight
                               text: Tr.t(modelData.text); color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: 13; font.weight: Font.DemiBold }
                        Text { visible: !!modelData.why; width: parent.width; wrapMode: Text.WordWrap
                               maximumLineCount: insItem.open ? 6 : 1; elide: Text.ElideRight
                               text: Tr.t(modelData.why || ""); color: Tokens.dim
                               font.family: Tokens.font; font.pixelSize: 12 }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: insItem.open = !insItem.open }
                }
            }
        }
    }

    MetricTile {                                    // ---- processor
        x: page.rx; y: page.y0; width: page.bigW; height: page.tileH
        title: Tr.t("Processor"); caption: page.cpuC.name || "CPU"; glyph: ""; tone: Tokens.cpu
        status: page.cpuC.status || "none"
        big: page.num(page.cpuC.use); bigUnit: "%"
        line1: page.join([(page.cpuC.approx ? "~" : "") + page.ghz(page.cpuC.clock_mhz),
                          page.cpuC.power_w !== null && page.cpuC.power_w !== undefined ? Math.round(page.cpuC.power_w) + " W" : ""])
        warning: page.cpuC.note || ""
        gauge: true; gaugeValue: page.cpuC.temp !== undefined ? page.cpuC.temp : null
        bar: page.cpuC.use !== null && page.cpuC.use !== undefined ? page.cpuC.use / 100 : -1
    }
    MetricTile {                                    // ---- memory
        x: page.rx + page.bigW + page.g; y: page.y0; width: page.smallW; height: page.tileH
        title: Tr.t("Memory"); caption: page.ramC.total_gb !== undefined ? Math.round(page.ramC.total_gb) + " GB RAM" : ""
        glyph: ""; tone: Tokens.ram
        status: page.ramC.status || "none"
        big: page.num(page.ramC.use); bigUnit: "%"
        line1: page.ramC.used_gb !== undefined ? page.ramC.used_gb.toFixed(1) + Tr.t(" GB used") : ""
        bar: page.ramC.use !== null && page.ramC.use !== undefined ? page.ramC.use / 100 : -1
    }
    MetricTile {                                    // ---- storage
        x: page.rx + page.bigW + page.smallW + 2 * page.g; y: page.y0; width: page.smallW; height: page.tileH
        title: Tr.t("Storage"); caption: page.diskC.mount ? Tr.t("Drive ") + page.diskC.mount : ""
        glyph: ""; tone: Tokens.disk
        status: page.diskC.status || "none"
        big: page.num(page.diskC.free_gb); bigUnit: " GB"
        line1: page.diskC.total_gb !== undefined ? Tr.t("free of ") + Math.round(page.diskC.total_gb) + " GB" : ""
        bar: page.diskC.use !== null && page.diskC.use !== undefined ? page.diskC.use / 100 : -1
    }
    MetricTile {                                    // ---- graphics card
        x: page.rx; y: page.y0 + page.tileH + page.g; width: page.bigW; height: page.tileH
        title: Tr.t("Graphics card"); caption: page.gpuC.name || "GPU"; glyph: ""; tone: Tokens.gpu
        status: page.gpuC.status || "none"
        big: page.num(page.gpuC.use); bigUnit: "%"
        line1: page.join([page.ghz(page.gpuC.clock_mhz),
                          page.gpuC.power_w !== null && page.gpuC.power_w !== undefined ? Math.round(page.gpuC.power_w) + " W" : ""])
        gauge: true; gaugeValue: page.gpuC.temp !== undefined ? page.gpuC.temp : null
        bar: page.gpuC.use !== null && page.gpuC.use !== undefined ? page.gpuC.use / 100 : -1
    }

    Card {                                          // ---- network
        x: page.rx + page.bigW + page.g; y: page.y0 + page.tileH + page.g; width: page.rw - page.bigW - page.g; height: page.tileH
        Rectangle { x: 18; y: 16; width: 34; height: 34; radius: 9; color: Tokens.tint(Tokens.cyan, 0.14)
                    Text { anchors.centerIn: parent; text: ""; color: Tokens.cyan
                           font.family: Tokens.iconFont; font.pixelSize: 17 } }
        Column {
            x: 62; y: 17; spacing: 1; width: parent.width - 62 - histBtn.width - 30
            Text { text: Tr.t("Network"); color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: 14; font.weight: Font.DemiBold }
            Text { width: parent.width; elide: Text.ElideRight
                   text: page.net.adapter ? Tr.line(page.net.adapter + (page.net.link ? "  ·  " + page.net.link + " Mbit/s" : ""))
                                          : Tr.t("Not connected")
                   color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 12 }
        }
        Pill { id: histBtn; anchors.right: parent.right; anchors.rightMargin: 16; y: 16; height: 30
               label: Tr.t("Usage history"); onClicked: page.go("Network usage") }
        Row {
            x: 18; y: 68; spacing: 22
            Repeater {
                model: 3
                Column {
                    spacing: 2
                    Text { text: [Tr.t("Download"), Tr.t("Upload"), Tr.t("Since start-up")][index]; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 12 }
                    Text { text: [page.net.down || "--", page.net.up || "--", page.net.since_boot || "--"][index]
                           color: [Tokens.cyan, Tokens.violet, Tokens.text][index]
                           font.family: Tokens.fontDisplay; font.pixelSize: 20; font.weight: Font.DemiBold }
                }
            }
        }
        Sparkline {
            x: 18; y: parent.height - 34; width: parent.width - 36; height: 24
            values: page.net.hist || []
            maxValue: { var m = 1; var h = values || []; for (var i = 0; i < h.length; ++i) if (h[i] > m) m = h[i]; return m * 1.15 }
            color: Tokens.cyan; fill: true
        }
    }

    Card {                                          // ---- performance chart
        x: 0; y: page.y1; width: page.perfW; height: page.botH
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
        Segmented { anchors.right: parent.right; anchors.rightMargin: 18; y: 14; width: 170
                    model: backend.rangeNames; index: backend.rangeIndex
                    onPicked: function (i) { backend.setRange(i) } }
        GraphChart {
            x: 14; y: 70; width: parent.width - 30; height: parent.height - 70 - 14
            series: [page.pd.c_use || [], page.pd.r_use || [], page.pd.g_use || []]
            colors: [Tokens.cpu, Tokens.ram, Tokens.gpu]; fill: false; maxValue: 100; unit: "%"
            slots: page.pd.points || 60; slotMs: page.pd.slot_ms || 1000
            scrollEnd: page.pd.end_ms || 0; extra: page.pd.extra || 0
            delayMs: page.pd.delay_ms || 0; nowMs: Clock.now
        }
    }

    Card {                                          // ---- right now
        id: nowCard
        x: page.perfW + page.g; y: page.y1; width: page.nowW; height: page.botH
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
        FitBar { x: 18; y: 48; width: parent.width - 36; height: 42
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
            x: 20; y: 100; width: parent.width - 40
            Repeater {
                model: 5                    // fixed rows: only their texts change each second
                Item {
                    id: fact
                    readonly property var f: nowCard.facts[index] || ({})
                    width: parent.width; height: Math.min(36, (nowCard.height - 112) / 5)
                    Rectangle { visible: index > 0; width: parent.width; height: 1; color: Tokens.line }
                    Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t(fact.f.t || ""); color: Tokens.sub
                           width: parent.width * 0.42; elide: Text.ElideRight
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                           width: parent.width * 0.56; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                           text: fact.f.v || ""; color: fact.f.on ? Tokens.text : Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                           font.weight: fact.f.on === true ? Font.DemiBold : Font.Normal }
                }
            }
        }
    }

    Card {                                          // ---- this PC
        id: pcCard
        x: page.perfW + page.nowW + 2 * page.g; y: page.y1; width: page.pcW; height: page.botH
        Text { x: 20; y: 16; text: Tr.t("This PC"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
        Text { x: 20; y: 40; width: parent.width - 40; elide: Text.ElideRight
               text: page.pc.windows || ""; color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 12 }
        readonly property var items: [
            {t: "Up time", v: page.pc.uptime || "--", c: Tokens.text},
            {t: "Battery", v: page.pc.battery ? Tr.line(page.pc.battery.pct + "%  ·  " + Tr.t(page.pc.battery.plugged ? "plugged in" : "on battery"))
                                             : Tr.t("No battery"), c: Tokens.text},
            {t: "Power plan", v: page.pc.plan || "--", c: Tokens.text},
            {t: "PC check", v: page.pc.score !== null && page.pc.score !== undefined ? page.pc.score + " / 100" : Tr.t("Not scanned yet"),
             c: page.pc.score !== null && page.pc.score !== undefined ? (page.pc.score >= 80 ? Tokens.accent : page.pc.score >= 60 ? Tokens.warn : Tokens.danger) : Tokens.accent,
             link: true}
        ]
        Column {
            x: 20; y: 68; width: parent.width - 40; spacing: 10
            Repeater {
                model: 4
                Column {
                    id: pcItem
                    readonly property var it: pcCard.items[index] || ({})
                    width: parent.width; spacing: 1
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
