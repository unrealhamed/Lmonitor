import QtQuick
import Lmonitor

// Smooth live lines. Drawing happens once per sample (in a render thread);
// between samples the finished picture just slides left on the GPU, so the
// motion is continuous and the UI thread stays free.
// series: [[v, v, ...], ...] oldest first, null = no data.
Item {
    id: root
    property var series: []
    property var colors: []
    property real maxValue: 100
    property bool fill: true
    property int slots: 60              // points visible across the width
    property bool slide: true
    property int interval: 1000
    property real lineWidth: 2
    readonly property real step: slots > 1 && width > 0 ? width / (slots - 1) : 1
    clip: true

    function repaint() { cv.requestPaint() }
    onSeriesChanged: repaint()
    onColorsChanged: repaint()
    onMaxValueChanged: repaint()
    onSlotsChanged: repaint()
    onWidthChanged: repaint()
    onHeightChanged: repaint()

    property real t0: 0
    readonly property real progress: !slide || t0 <= 0 || interval <= 0 ? 0
        : Math.max(0, Math.min(1, (Clock.now - t0) / interval))
    Canvas {
        id: cv
        x: -root.step * root.progress
        width: root.width + root.step; height: root.height
        renderStrategy: Canvas.Threaded
        renderTarget: Canvas.FramebufferObject
        onPainted: root.t0 = Date.now()      // the new picture starts sliding now
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var W = root.width, H = height, st = root.step, mx = root.maxValue > 0 ? root.maxValue : 1
            if (W <= 0 || H <= 0) return
            var n = root.slide ? root.slots + 1 : root.slots
            var all = root.series || []
            for (var si = 0; si < all.length; ++si) {
                var arr = all[si] || []
                var c = root.colors[si] !== undefined ? root.colors[si] : Tokens.cyan
                var pts = []
                for (var j = 0; j < n; ++j) {
                    var src = arr.length - n + j
                    var v = src >= 0 ? arr[src] : null
                    pts.push(v === null || v === undefined ? null
                             : [j * st, H - 2 - Math.min(Math.max(v, 0), mx) / mx * (H - 4)])
                }
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
                for (var q = 0; q < pts.length; ++q) { if (pts[q] === null) flush(); else seg.push(pts[q]) }
                flush()
            }
        }
    }
}
