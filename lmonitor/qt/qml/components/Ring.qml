import QtQuick
import Lmonitor

// Temperature ring. value: 0..100 (°C) or null = no sensor (empty ring, "--").
Item {
    id: root
    property var value: null
    property color color: Tokens.cyan
    property string unitText: "Celsius"
    onValueChanged: cv.requestPaint()
    onColorChanged: cv.requestPaint()
    Canvas {
        id: cv
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var r = Math.min(width, height) / 2 - 6, cx = width / 2, cy = height / 2
            var a0 = 0.75 * Math.PI, sweep = 1.5 * Math.PI
            ctx.lineWidth = 8; ctx.lineCap = "round"
            ctx.strokeStyle = "#26262c"
            ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + sweep); ctx.stroke()
            if (root.value !== null && root.value !== undefined) {
                var f = Math.max(0.02, Math.min(1, root.value / 100))
                ctx.strokeStyle = root.color
                ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + sweep * f); ctx.stroke()
            }
        }
    }
    Column {
        anchors.centerIn: parent
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: root.value === null || root.value === undefined ? "--" : Math.round(root.value) + "°"
               color: Tokens.text; font.family: Tokens.font; font.pixelSize: 24; font.bold: true }
        Text { anchors.horizontalCenter: parent.horizontalCenter
               text: root.value === null || root.value === undefined ? "no sensor" : root.unitText
               color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
    }
}
