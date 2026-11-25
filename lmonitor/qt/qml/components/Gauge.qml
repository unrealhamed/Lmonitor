import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Temperature gauge: a 270-degree arc; the number sits in the exact middle.
// value: 0..100 (°C) or null = no sensor ("--").
Item {
    id: root
    property var value: null
    property color color: Tokens.cyan
    readonly property bool has: value !== null && value !== undefined
    implicitWidth: 76; implicitHeight: 76
    onValueChanged: cv.requestPaint()
    onColorChanged: cv.requestPaint()
    Connections { target: Tokens; function onLineStrongChanged() { cv.requestPaint() } }
    Canvas {
        id: cv
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var r = Math.min(width, height) / 2 - 5, cx = width / 2, cy = height / 2
            var a0 = 0.75 * Math.PI, sweep = 1.5 * Math.PI
            ctx.lineWidth = 7; ctx.lineCap = "round"
            ctx.strokeStyle = Tokens.lineStrong
            ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + sweep); ctx.stroke()
            if (root.has) {
                ctx.strokeStyle = root.color
                ctx.beginPath(); ctx.arc(cx, cy, r, a0, a0 + sweep * Math.max(0.02, Math.min(1, root.value / 100))); ctx.stroke()
            }
        }
    }
    Text {
        id: num
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: -5
        text: root.has ? Math.round(root.value) : "--"
        color: Tokens.text; font.family: Tokens.fontDisplay; font.pixelSize: 20; font.weight: Font.Bold
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter; anchors.top: num.bottom; anchors.topMargin: -2
        text: root.has ? "°C" : Tr.t("no sensor")
        color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 11
    }
}
