import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// The graph overlay ("HUD"): small live charts for gaming. Used by the real overlay
// window AND the settings preview, so the preview is exactly what the game shows.
// info:  {items: [{key, title, unit, text, series, max, lo, hi, color}], accent}
// style: backend.settings (hud_* keys)
// Motion "smooth": a new reading is drawn outside the plot and slides in at a constant
// speed (the picture is only moved per frame, it is painted again only when new numbers
// arrive). Motion "saver": one step per reading, nothing moves in between.
// Its size comes from the settings only (it never resizes itself over a game).
Item {
    id: hud
    // Persian: inside the mirrored main window this turns itself back, so time runs left to right
    property bool upright: false
    onUprightChanged: Tr.rev++                  // texts inside check their direction again
    function checkUpright() { hud.upright = Tr.rtl && hud.parent !== null && Tr.mirrored(hud.parent) }
    transform: Scale { origin.x: hud.width / 2; xScale: hud.upright ? -1 : 1 }
    Component.onCompleted: Qt.callLater(function () { hud.checkUpright() })
    Connections { target: Tr; function onLangChanged() { Qt.callLater(function () { hud.checkUpright() }) } }
    property var info: ({items: [], accent: "#35d6ff"})
    property var style: ({})
    readonly property var keys: style.hud_items || []
    readonly property int count: Math.max(1, keys.length)
    readonly property string size: style.hud_size || "m"
    readonly property string layout: style.hud_layout || "v"
    readonly property bool gaming: (style.hud_style || "hud") === "hud"
    readonly property color accent: info && info.accent ? info.accent : "#35d6ff"
    readonly property real alpha: (style.hud_alpha === undefined ? 65 : style.hud_alpha) / 100
    property bool animate: true                          // false: never move (hidden page)
    readonly property bool smooth: (style.hud_motion || "smooth") === "smooth" && animate
    readonly property int points: info && info.points ? info.points : 60
    readonly property int extra: info && info.extra ? info.extra : 0
    readonly property real slotMs: info && info.slot_ms ? info.slot_ms : 1000
    readonly property real endMs: info && info.end_ms ? info.end_ms : 0
    readonly property real delayMs: info && info.delay_ms ? info.delay_ms : 0
    property real nowMs: 0
    // One clock for every chart. The line moves slowly (a few pixels a second), so the
    // window is redrawn only when it has moved about 1/3 pixel (16..100 ms) - not at the
    // screen's full refresh rate. Measured: same smoothness, far less work during a game.
    readonly property real pxPerMs: points > 1 ? (tileW / (points - 1)) / slotMs : 0
    readonly property int tickMs: pxPerMs > 0 ? Math.max(16, Math.min(100, Math.round(0.33 / pxPerMs))) : 100
    Timer {
        interval: hud.tickMs; repeat: true
        running: hud.smooth && hud.visible
        onTriggered: hud.nowMs = Date.now()
    }

    readonly property real k: size === "s" ? 0.8 : size === "l" ? 1.3 : 1.0
    readonly property real pad: Math.round(10 * k)
    readonly property real gap: Math.round(8 * k)
    readonly property real tileW: Math.round(220 * k)
    readonly property real valuePx: Math.round(24 * k)
    readonly property real titlePx: Math.max(9, Math.round(10 * k))
    readonly property real chartH: Math.round(40 * k)
    readonly property real headH: valuePx + titlePx + 6
    readonly property real tileH: headH + chartH + 4
    readonly property int cols: layout === "h" ? count : layout === "grid" ? Math.min(2, count) : 1
    readonly property int rows: Math.ceil(count / cols)
    implicitWidth: cols * tileW + (cols - 1) * gap + 2 * pad
    implicitHeight: rows * tileH + (rows - 1) * gap + 2 * pad
    width: implicitWidth; height: implicitHeight

    readonly property string numFont: "Bahnschrift"     // Windows' condensed "DIN" face
    readonly property string labelFont: Tokens.font

    // one entry per chosen chart, even before the first numbers arrive
    function itemFor(i) {
        var list = info && info.items ? info.items : []
        for (var j = 0; j < list.length; ++j) if (list[j].key === keys[i]) return list[j]
        return {key: keys[i], title: "", unit: "", text: "--", series: [], max: 100, lo: "--", hi: "--",
                color: accent}
    }

    // ---- panel
    Rectangle {
        anchors.fill: parent
        radius: hud.gaming ? 4 : 12
        color: Qt.rgba(0.02, 0.025, 0.04, hud.alpha)
        border.width: 1
        border.color: Qt.rgba(hud.accent.r, hud.accent.g, hud.accent.b, hud.gaming ? 0.35 : 0.18)
    }
    Rectangle {                                  // faint accent wash, top to bottom
        visible: hud.gaming && hud.alpha > 0
        anchors.fill: parent; anchors.margins: 1; radius: 3
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(hud.accent.r, hud.accent.g, hud.accent.b, 0.10 * hud.alpha) }
            GradientStop { position: 1.0; color: "transparent" }
        }
    }
    // corner brackets (gaming style)
    Repeater {
        model: hud.gaming ? 4 : 0
        Item {
            id: corner
            readonly property bool atRight: index === 1 || index === 3
            readonly property bool atBottom: index >= 2
            readonly property real len: Math.round(12 * hud.k)
            x: atRight ? hud.width - len : 0; y: atBottom ? hud.height - len : 0
            width: len; height: len
            Rectangle { width: corner.len; height: 2; color: hud.accent; y: corner.atBottom ? corner.len - 2 : 0 }
            Rectangle { width: 2; height: corner.len; color: hud.accent; x: corner.atRight ? corner.len - 2 : 0 }
        }
    }

    // ---- tiles
    Repeater {
        model: hud.keys.length
        Item {
            id: tile
            readonly property var it: hud.itemFor(index)
            readonly property int col: index % hud.cols
            readonly property int row: Math.floor(index / hud.cols)
            readonly property color c: it.color || hud.accent
            x: hud.pad + col * (hud.tileW + hud.gap)
            y: hud.pad + row * (hud.tileH + hud.gap)
            width: hud.tileW; height: hud.tileH

            Rectangle {                          // separator between stacked tiles
                visible: tile.row > 0
                y: -hud.gap / 2; width: parent.width; height: 1
                color: Qt.rgba(1, 1, 1, 0.08)
            }
            Rectangle { x: 0; y: 2; width: 3; height: hud.titlePx + 2; color: tile.c; visible: hud.gaming }
            Text {
                x: hud.gaming ? 8 : 0; y: 0
                text: Tr.t(tile.it.title || "").toUpperCase()
                color: Qt.rgba(1, 1, 1, 0.62)
                font.family: hud.labelFont; font.pixelSize: hud.titlePx; font.bold: true
                font.letterSpacing: 1.2
            }
            Text {                               // min / max of what the chart shows
                anchors.right: parent.right; y: 0
                text: "▼" + tile.it.lo + "  ▲" + tile.it.hi
                color: Qt.rgba(1, 1, 1, 0.42)
                font.family: hud.numFont; font.pixelSize: hud.titlePx
            }
            Row {
                y: hud.titlePx + 3; spacing: 4
                Text {
                    text: tile.it.text
                    color: tile.it.text === "--" ? Qt.rgba(1, 1, 1, 0.4) : "white"
                    font.family: hud.numFont; font.pixelSize: hud.valuePx; font.bold: true
                    style: hud.gaming ? Text.Outline : Text.Normal
                    styleColor: Qt.rgba(tile.c.r, tile.c.g, tile.c.b, 0.35)
                }
                Text {
                    anchors.baseline: parent.children[0].baseline
                    text: tile.it.unit === "%" ? "%" : (tile.it.unit || "")
                    color: tile.c
                    font.family: hud.numFont; font.pixelSize: Math.round(hud.valuePx * 0.5); font.bold: true
                }
            }
            Item {                                   // the plot: a still grid + a sliding line
                id: plot
                y: hud.headH + 2; width: parent.width; height: hud.chartH
                clip: true
                Repeater {
                    model: 3
                    Rectangle { width: plot.width; height: 1; color: Qt.rgba(1, 1, 1, 0.07)
                                y: Math.round(index * (plot.height - 1) / 2) }
                }
                readonly property real step: hud.points > 1 ? width / (hud.points - 1) : width
                property real drawnEnd: 0            // end_ms of the picture on screen
                Canvas {
                    id: cv
                    objectName: "hudPlot" + index     // read by the smoothness test
                    readonly property real stepPx: plot.step
                    readonly property real drawnEndMs: plot.drawnEnd
                    readonly property real minX: plot.width - width
                    readonly property real restX: -hud.extra * plot.step   // newest point at the right edge
                    x: !hud.smooth || plot.drawnEnd <= 0 ? Math.max(minX, restX)
                       : Math.min(0, Math.max(minX, -plot.step * ((hud.nowMs - hud.delayMs - plot.drawnEnd) / hud.slotMs + hud.extra)))
                    width: plot.width + (hud.extra + 1) * plot.step; height: plot.height
                    renderStrategy: Canvas.Immediate   // picture and position change in the same frame
                    readonly property var vals: tile.it.series || []
                    onValsChanged: requestPaint()
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    Connections { target: hud; function onGamingChanged() { cv.requestPaint() }
                                  function onAccentChanged() { cv.requestPaint() } }
                    onPaint: {
                        plot.drawnEnd = hud.endMs
                        var ctx = getContext("2d")
                        ctx.reset()
                        var H = height, v = vals, n = v.length, st = plot.step, c = tile.c
                        var mx = tile.it.max > 0 ? tile.it.max : 100
                        if (n < 2) return
                        var pts = []
                        for (var i = 0; i < n; ++i) {
                            var x = v[i]
                            pts.push(x === null || x === undefined ? null
                                     : [i * st, H - 1.5 - Math.min(Math.max(x, 0), mx) / mx * (H - 3)])
                        }
                        var segs = [], seg = []
                        for (var p = 0; p < pts.length; ++p) {
                            if (pts[p] === null) { if (seg.length > 1) segs.push(seg); seg = [] }
                            else seg.push(pts[p])
                        }
                        if (seg.length > 1) segs.push(seg)
                        for (var s = 0; s < segs.length; ++s) {
                            var sg = segs[s]
                            ctx.beginPath(); ctx.moveTo(sg[0][0], H)              // area
                            for (var a = 0; a < sg.length; ++a) ctx.lineTo(sg[a][0], sg[a][1])
                            ctx.lineTo(sg[sg.length - 1][0], H); ctx.closePath()
                            var gr = ctx.createLinearGradient(0, 0, 0, H)
                            gr.addColorStop(0, Qt.rgba(c.r, c.g, c.b, hud.gaming ? 0.32 : 0.22))
                            gr.addColorStop(1, Qt.rgba(c.r, c.g, c.b, 0))
                            ctx.fillStyle = gr; ctx.fill()
                            var passes = hud.gaming ? [[5, 0.18], [1.8, 1]] : [[1.6, 1]]   // glow, line
                            for (var q = 0; q < passes.length; ++q) {
                                ctx.beginPath(); ctx.moveTo(sg[0][0], sg[0][1])
                                for (var b = 1; b < sg.length; ++b) ctx.lineTo(sg[b][0], sg[b][1])
                                ctx.strokeStyle = Qt.rgba(c.r, c.g, c.b, passes[q][1])
                                ctx.lineWidth = passes[q][0]; ctx.lineJoin = "round"; ctx.lineCap = "round"
                                ctx.stroke()
                            }
                        }
                        var lastP = null                                         // the newest point
                        for (var r = pts.length - 1; r >= 0 && lastP === null; --r) lastP = pts[r]
                        if (lastP !== null) {
                            if (hud.gaming) {
                                ctx.fillStyle = Qt.rgba(c.r, c.g, c.b, 0.30)
                                ctx.beginPath(); ctx.arc(lastP[0], lastP[1], 5, 0, 2 * Math.PI); ctx.fill()
                            }
                            ctx.fillStyle = "white"
                            ctx.beginPath(); ctx.arc(lastP[0], lastP[1], 2.2, 0, 2 * Math.PI); ctx.fill()
                        }
                    }
                }
            }
        }
    }
}
