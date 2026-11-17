import QtQuick
import Lmonitor
import "."                      // components/Text.qml

// The small moving picture of one "What's new" slide. One clock `t` (0..1, again and again)
// drives everything, so nothing runs while the box is closed (`running`).
// art: netusage / hours / meter / frametime / smooth / anything else (a plain pulse)
Item {
    id: art
    property string kind: ""
    property bool running: false
    property real t: 0
    readonly property color cDown: Tokens.cyan
    readonly property color cUp: Tokens.violet
    NumberAnimation on t { from: 0; to: 1; duration: 3600; loops: Animation.Infinite; running: art.running }
    onRunningChanged: if (running) t = 0

    function clamp(x) { return Math.max(0, Math.min(1, x)) }
    function ease(x) { x = clamp(x); return 1 - Math.pow(1 - x, 3) }
    // 0 -> 1 between t = a and t = b
    function step(a, b) { return ease((t - a) / (b - a)) }

    // ---- network usage: day bars grow one after the other, one day gets picked
    Item {
        visible: art.kind === "netusage"
        anchors.centerIn: parent; width: 300; height: 150
        readonly property var days: [0.35, 0.6, 0.25, 0.8, 0.5, 1.0, 0.45, 0.7, 0.3, 0.55]
        Repeater {
            model: 10
            Item {
                readonly property real g: art.step(0.03 * index, 0.03 * index + 0.3)
                readonly property real full: 118 * parent.days[index]
                x: index * 30; width: 30; height: 150
                Rectangle { visible: index === 5; anchors.fill: parent; anchors.margins: 1; radius: 5
                            opacity: art.step(0.5, 0.62); color: Tokens.accentA(0.16)
                            border.width: 1; border.color: Tokens.accent }
                Rectangle { id: nd; x: 7; width: 16; radius: 3; color: art.cDown
                            height: parent.full * 0.8 * parent.g; y: 142 - height }
                Rectangle { x: 7; width: 16; radius: 3; color: art.cUp
                            height: parent.full * 0.2 * parent.g; y: nd.y - height }
            }
        }
    }

    // ---- hour list: rows slide in, their bars fill, one row is chosen
    Column {
        visible: art.kind === "hours"
        anchors.centerIn: parent; width: 300; spacing: 6
        Repeater {
            model: [["14:00 - 15:00", 0.35, "420 MB"], ["15:00 - 16:00", 0.6, "730 MB"],
                    ["16:00 - 17:00", 1.0, "1.2 GB"], ["17:00 - 18:00", 0.2, "240 MB"]]
            Rectangle {
                readonly property real g: art.step(0.08 * index, 0.08 * index + 0.22)
                readonly property real pick: index === 2 ? art.step(0.6, 0.72) : 0
                width: 300; height: 32; radius: 7; opacity: g
                transform: Translate { x: (1 - g) * 40 }
                color: pick > 0 ? Tokens.accentA(0.16 * pick) : Tokens.fg(0.05)
                border.width: pick > 0.5 ? 1 : 0; border.color: Tokens.accent
                Text { x: 10; y: 4; text: modelData[0]; color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 11; font.bold: true }
                Text { anchors.right: parent.right; anchors.rightMargin: 10; y: 4; text: modelData[2]; color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 11; font.bold: true }
                Rectangle { x: 10; y: 22; width: 280; height: 4; radius: 2; color: Tokens.track
                            Rectangle { height: 4; radius: 2; color: art.cDown
                                        width: 280 * modelData[1] * art.step(0.08 * index + 0.15, 0.08 * index + 0.5) } }
            }
        }
    }

    // ---- own meter: a pulse once a "minute", the amount counts up
    Item {
        visible: art.kind === "meter"
        anchors.centerIn: parent; width: 300; height: 150
        readonly property real beat: (art.t * 4) % 1
        Rectangle { anchors.centerIn: dot; width: 26 + 70 * parent.beat; height: width; radius: width / 2
                    color: "transparent"; border.width: 2; border.color: Tokens.accent; opacity: 1 - parent.beat }
        Rectangle { id: dot; x: 40; y: 62; width: 26; height: 26; radius: 13; color: Tokens.accent }
        Text { x: 120; y: 36; text: (120 + Math.floor(art.t * 4) * 85 + Math.round(85 * art.ease(parent.beat * 2))) + " MB"
               color: Tokens.text; font.family: Tokens.font; font.pixelSize: 34; font.bold: true }
        Row { x: 120; y: 92; spacing: 5
              Repeater { model: 8
                         Rectangle { width: 14; height: 8 + 26 * [0.3, 0.6, 0.4, 0.9, 0.5, 0.7, 0.35, 0.8][index]
                                     radius: 2; color: art.cDown; anchors.bottom: parent.bottom
                                     opacity: index <= Math.floor(art.t * 8) ? 1 : 0.15 } } }
    }

    // ---- frame time: before (broken, "--") and now (one steady line being drawn)
    Canvas {
        id: ftCanvas
        visible: art.kind === "frametime"
        anchors.centerIn: parent; width: 300; height: 150
        readonly property real p: art.t
        onPChanged: if (visible) requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var dim = Tokens.fg(0.28), a = Tokens.accent
            ctx.lineWidth = 2.5; ctx.lineCap = "round"; ctx.lineJoin = "round"
            ctx.strokeStyle = dim                                   // before: pieces
            var segs = [[10, 60], [85, 120], [150, 205], [235, 290]]
            for (var i = 0; i < segs.length; ++i) {
                ctx.beginPath(); ctx.moveTo(segs[i][0], 38 + (i % 2) * 5); ctx.lineTo(segs[i][1], 40 - (i % 2) * 4); ctx.stroke()
            }
            var end = 10 + 280 * art.ease(p * 1.5)                  // now: one line
            ctx.strokeStyle = a; ctx.beginPath()
            for (var x = 10; x <= end; x += 6) {
                var y = 112 + Math.sin(x / 19) * 5 + Math.sin(x / 7) * 2
                if (x === 10) ctx.moveTo(x, y); else ctx.lineTo(x, y)
            }
            ctx.stroke()
            ctx.fillStyle = "white"; ctx.beginPath(); ctx.arc(end, 112 + Math.sin(end / 19) * 5 + Math.sin(end / 7) * 2, 3.5, 0, 2 * Math.PI); ctx.fill()
        }
        Text { x: 10; y: 6; text: "--  ms"; color: Tokens.fg(0.35); font.family: Tokens.font; font.pixelSize: 13; font.bold: true }
        Text { x: 10; y: 76; text: "7.0 ms"; color: Tokens.text; font.family: Tokens.font; font.pixelSize: 13; font.bold: true }
    }

    // ---- charts in one piece: two lines scrolling without a break
    Canvas {
        id: smCanvas
        visible: art.kind === "smooth"
        anchors.centerIn: parent; width: 300; height: 150
        readonly property real p: art.t
        onPChanged: if (visible) requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            ctx.strokeStyle = Tokens.line; ctx.lineWidth = 1
            for (var g = 0; g < 3; ++g) { ctx.beginPath(); ctx.moveTo(0, 20 + g * 55); ctx.lineTo(300, 20 + g * 55); ctx.stroke() }
            var cols = [Tokens.cyan, Tokens.violet], off = p * 2 * Math.PI
            ctx.lineWidth = 2.5; ctx.lineJoin = "round"
            for (var k = 0; k < 2; ++k) {
                ctx.strokeStyle = cols[k]; ctx.beginPath()
                for (var x = 0; x <= 300; x += 5) {
                    var y = 50 + k * 50 + Math.sin(x / 30 + off * (k + 1)) * 16 + Math.sin(x / 11 + off * 2) * 4
                    if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                }
                ctx.stroke()
            }
        }
    }

    // ---- a new look: cards fall into place one by one
    Item {
        visible: art.kind === "design"
        anchors.centerIn: parent; width: 300; height: 150
        Rectangle { x: 0; y: 0; width: 70; height: 150; radius: 8; color: Tokens.bg1; border.width: 1; border.color: Tokens.line
                    opacity: art.step(0, 0.15)
                    Column { x: 10; y: 12; spacing: 9
                             Repeater { model: 5
                                        Row { spacing: 6; opacity: art.step(0.08 + index * 0.05, 0.2 + index * 0.05)
                                              Rectangle { width: 9; height: 9; radius: 3; color: index === 0 ? Tokens.accent : Tokens.lineStrong }
                                              Rectangle { width: 30; height: 7; radius: 3; y: 1; color: index === 0 ? Tokens.accentA(0.5) : Tokens.lineStrong } } } } }
        Repeater {
            model: 4
            Rectangle {
                readonly property real g: art.step(0.2 + index * 0.08, 0.42 + index * 0.08)
                x: 82 + (index % 2) * 112; y: 4 + Math.floor(index / 2) * 74 + (1 - g) * 18
                width: 104; height: 66; radius: 8; opacity: g
                color: Tokens.card; border.width: 1; border.color: Tokens.line
                Rectangle { x: 10; y: 10; width: 18; height: 18; radius: 5; color: Tokens.tint([Tokens.cyan, Tokens.violet, Tokens.green, Tokens.orange][index], 0.2) }
                Rectangle { x: 10; y: 38; width: 34 + 20 * parent.g; height: 10; radius: 3; color: Tokens.text; opacity: 0.85 }
                Rectangle { x: 10; y: 54; width: 70; height: 4; radius: 2; color: Tokens.lineStrong
                            Rectangle { width: parent.width * 0.6 * parent.parent.g; height: 4; radius: 2
                                        color: [Tokens.cyan, Tokens.violet, Tokens.green, Tokens.orange][index] } }
            }
        }
    }

    // ---- light and dark: a window turns from one mode to the other
    Item {
        visible: art.kind === "lightdark"
        anchors.centerIn: parent; width: 300; height: 150
        readonly property real m: art.t < 0.5 ? art.step(0.15, 0.4) : 1 - art.step(0.65, 0.9)   // 0 dark .. 1 light
        function mix(a, b) { return Qt.rgba(a.r + (b.r - a.r) * m, a.g + (b.g - a.g) * m, a.b + (b.b - a.b) * m, 1) }
        Rectangle {
            anchors.fill: parent; radius: 10; clip: true
            color: parent.mix(Qt.color("#0E1014"), Qt.color("#F3F4F6"))
            border.width: 1; border.color: parent.mix(Qt.color("#252A32"), Qt.color("#E3E6EA"))
            Rectangle { x: 1; y: 1; width: 78; height: parent.height - 2; color: parent.parent.mix(Qt.color("#15181D"), Qt.color("#FFFFFF")) }
            Repeater { model: 3
                       Rectangle { x: 92; y: 14 + index * 44; width: 194; height: 34; radius: 7
                                   color: parent.parent.mix(Qt.color("#15181D"), Qt.color("#FFFFFF"))
                                   border.width: 1; border.color: parent.parent.mix(Qt.color("#252A32"), Qt.color("#E3E6EA"))
                                   Rectangle { x: 10; y: 12; width: 60 + index * 25; height: 9; radius: 4
                                               color: parent.parent.parent.mix(Qt.color("#ECEFF3"), Qt.color("#12151A")) } } }
            Rectangle { x: 12; y: 16; width: 54; height: 9; radius: 4; color: Tokens.accent }
        }
        Text { anchors.right: parent.right; anchors.rightMargin: 10; y: 6
               text: parent.m > 0.5 ? "\uE706" : "\uE708"; color: Tokens.accent; font.family: Tokens.iconFont; font.pixelSize: 18 }
    }

    // ---- a new Home: four cards, the numbers count up, the gauge fills
    Item {
        visible: art.kind === "dashboard"
        anchors.centerIn: parent; width: 300; height: 150
        Repeater {
            model: 4
            Rectangle {
                readonly property real g: art.step(0.05 + index * 0.07, 0.35 + index * 0.07)
                readonly property color tone: [Tokens.cyan, Tokens.violet, Tokens.green, Tokens.orange][index]
                x: index * 76; y: 18; width: 70; height: 112; radius: 8; opacity: Math.min(1, g * 2)
                color: Tokens.card; border.width: 1; border.color: Tokens.line
                Text { x: 8; y: 8; text: Math.round([41, 64, 29, 256][index] * parent.g) + (index === 3 ? "" : "%")
                       color: Tokens.text; font.family: Tokens.fontDisplay; font.pixelSize: 17; font.weight: Font.DemiBold }
                Canvas {
                    visible: index < 2
                    x: 13; y: 40; width: 44; height: 44
                    readonly property real f: parent.g
                    onFChanged: requestPaint()
                    onPaint: {
                        var c = getContext("2d"); c.reset(); c.lineWidth = 5; c.lineCap = "round"
                        c.strokeStyle = Tokens.lineStrong; c.beginPath(); c.arc(22, 22, 17, 0.75 * Math.PI, 2.25 * Math.PI); c.stroke()
                        c.strokeStyle = parent.tone; c.beginPath(); c.arc(22, 22, 17, 0.75 * Math.PI, 0.75 * Math.PI + 1.5 * Math.PI * 0.6 * f); c.stroke()
                    }
                }
                Rectangle { visible: index >= 2; x: 8; y: 92; width: 54; height: 5; radius: 3; color: Tokens.lineStrong
                            Rectangle { height: 5; radius: 3; color: parent.parent.tone; width: parent.width * 0.55 * parent.parent.g } }
            }
        }
    }

    // ---- fewer settings: many choices fade away, two stay
    Item {
        visible: art.kind === "simple"
        anchors.centerIn: parent; width: 300; height: 150
        readonly property real gone: art.step(0.25, 0.55)
        Repeater {
            model: 12
            Rectangle {
                readonly property bool keep: index === 5 || index === 6
                x: 18 + (index % 4) * 68; y: 14 + Math.floor(index / 4) * 44
                width: 58; height: 32; radius: 8
                opacity: keep ? 1 : 1 - parent.gone
                scale: keep ? 1 + 0.12 * parent.gone : 1 - 0.3 * parent.gone
                color: keep ? Tokens.accentA(0.18) : Tokens.fg(0.06)
                border.width: 1; border.color: keep ? Tokens.accent : Tokens.line
                Text { anchors.centerIn: parent; visible: parent.keep; text: index === 5 ? "\uE706" : "\uE708"
                       color: Tokens.accent; font.family: Tokens.iconFont; font.pixelSize: 15 }
            }
        }
    }

    // ---- anything else: a calm pulse
    Rectangle {
        visible: ["netusage", "hours", "meter", "frametime", "smooth", "design", "lightdark", "dashboard", "simple"].indexOf(art.kind) < 0
        anchors.centerIn: parent; width: 60 + 20 * Math.sin(art.t * 2 * Math.PI); height: width; radius: width / 2
        color: Tokens.accentA(0.25); border.width: 2; border.color: Tokens.accent
    }
}
