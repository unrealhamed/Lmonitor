import QtQuick
import Lmonitor

// Graphs page chart: one or several lines that scroll at a constant speed.
// A new point is drawn outside the plot and rolls in with the scroll, so nothing ever pops
// in at the right edge. The picture is painted on the UI thread (Immediate), which puts a
// new picture and its new offset on screen in the same frame.
// series: [[v, ...], ...] oldest first, `slots + extra` points, null = no data.
Item {
    id: root
    property var series: []
    property var colors: []
    property real maxValue: 100
    property string unit: ""
    property bool fill: true
    property int slots: 60              // points visible across the plot
    property int extra: 0               // points kept outside the plot
    property real slotMs: 1000
    property real scrollEnd: 0          // clock time of the newest point
    property real delayMs: 0            // the right edge shows the clock minus this
    property real nowMs: 0              // set once per frame by the page
    property real lineWidth: 2
    property real rightMax: 0           // > 0: second scale on the right (fan RPM)
    property string rightKind: ""
    property string fmtKind: ""         // "net" / "rpm": how the scale numbers are written

    readonly property real leftGap: fmtKind === "" ? 44 : 62
    readonly property real rightGap: rightMax > 0 ? 58 : 0
    readonly property real plotW: Math.max(1, width - leftGap - rightGap)
    readonly property real step: slots > 1 ? plotW / (slots - 1) : 1
    property real drawnEnd: 0           // scrollEnd of the picture on screen

    function repaint() { cv.requestPaint() }
    onSeriesChanged: repaint()
    onColorsChanged: repaint()
    onMaxValueChanged: repaint()
    onFillChanged: repaint()
    onExtraChanged: repaint()
    onStepChanged: repaint()
    onHeightChanged: repaint()
    onVisibleChanged: if (visible) repaint()

    function label(max, f, u, kind) {
        var x = max * f
        if (kind === "net") return Tokens.fmtNet(x, backend.settings.net_unit)
        if (kind === "rpm") return Math.round(x) + Tr.t(" RPM")
        return (x >= 100 || Math.round(x) === x ? Math.round(x) : x.toFixed(1)) + u
    }
    Repeater {
        model: [1, 0.5, 0]
        Text { x: 0; y: root.height * index / 2 - 7; width: root.leftGap - 6
               text: root.label(root.maxValue, modelData, root.unit, root.fmtKind); color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: 10 }
    }
    Repeater {
        model: root.rightMax > 0 ? [1, 0.5, 0] : []
        Text { x: root.width - 52; y: root.height * index / 2 - 7; width: 52
               horizontalAlignment: Text.AlignRight
               text: root.label(root.rightMax, modelData, "", root.rightKind); color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: 10 }
    }
    Repeater {
        model: 3
        Rectangle { x: root.leftGap; width: root.plotW; height: 1; color: "#26262c"
                    y: Math.min(root.height - 1, Math.round(root.height * index / 2)) }
    }

    Item {
        x: root.leftGap; width: root.plotW; height: root.height
        clip: true
        Canvas {
            id: cv
            readonly property real minX: root.plotW - width
            // position of the newest point: plot right edge - time still to go, in pixels
            x: root.drawnEnd <= 0 ? minX
               : Math.min(0, Math.max(minX, -root.step * ((root.nowMs - root.delayMs - root.drawnEnd) / root.slotMs + root.extra)))
            width: root.plotW + (root.extra + 1) * root.step; height: root.height
            renderStrategy: Canvas.Immediate
            onPaint: {
                root.drawnEnd = root.scrollEnd
                var ctx = getContext("2d")
                ctx.reset()
                var H = height, st = root.step, mx = root.maxValue > 0 ? root.maxValue : 1
                if (width <= 0 || H <= 0) return
                var n = root.slots + root.extra
                var all = root.series || []
                for (var si = 0; si < all.length; ++si) {
                    var arr = all[si] || []
                    var c = root.colors[si] !== undefined ? root.colors[si] : Tokens.cyan
                    var seg = []
                    var flush = function () {
                        if (seg.length >= 2) {
                            if (root.fill) {
                                ctx.beginPath(); ctx.moveTo(seg[0][0], H)
                                for (var k = 0; k < seg.length; ++k) ctx.lineTo(seg[k][0], seg[k][1])
                                ctx.lineTo(seg[seg.length - 1][0], H); ctx.closePath()
                                var g = ctx.createLinearGradient(0, 0, 0, H)
                                g.addColorStop(0, Qt.rgba(c.r, c.g, c.b, 0.30)); g.addColorStop(1, Qt.rgba(c.r, c.g, c.b, 0))
                                ctx.fillStyle = g; ctx.fill()
                            }
                            ctx.beginPath(); ctx.moveTo(seg[0][0], seg[0][1])
                            for (var m = 1; m < seg.length; ++m) ctx.lineTo(seg[m][0], seg[m][1])
                            ctx.strokeStyle = c; ctx.lineWidth = root.lineWidth; ctx.lineJoin = "round"; ctx.stroke()
                        }
                        seg = []
                    }
                    for (var j = 0; j < n; ++j) {
                        var src = arr.length - n + j
                        var v = src >= 0 ? arr[src] : null
                        if (v === null || v === undefined) flush()
                        else seg.push([j * st, H - 2 - Math.min(Math.max(v, 0), mx) / mx * (H - 4)])
                    }
                    flush()
                }
            }
        }
    }
}
