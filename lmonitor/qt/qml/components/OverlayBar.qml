import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// The overlay bar. Used by the real overlay window AND the live previews, so
// what you see in the settings is what the game shows.
// model: {groups:[{name,color,items:[{key,label,text,color}]}], graph:[..]|null}
// style: backend.settings
// One Text per group (styled text) - few objects, cheap to update. Groups that
// change order glide to their new place.
Item {
    id: bar
    // Persian: inside the mirrored main window this turns itself back, so time runs left to right
    property bool upright: false
    onUprightChanged: Tr.rev++                  // texts inside check their direction again
    function checkUpright() { bar.upright = Tr.rtl && bar.parent !== null && Tr.mirrored(bar.parent) }
    transform: Scale { origin.x: bar.width / 2; xScale: bar.upright ? -1 : 1 }
    Connections { target: Tr; function onLangChanged() { Qt.callLater(function () { bar.checkUpright() }) } }
    property var model: ({groups: [], graph: null})
    property var style: ({})
    readonly property bool horizontal: (style.layout || "h") === "h"
    readonly property int px: Math.round((style.text || 11) * 1.4)
    readonly property bool glass: style.look === "glass"
    readonly property real bgAlpha: glass ? 0.16 : (style.alpha || 80) / 100
    property bool reorder: false
    // which screen edge the bar touches ("left", "right", "center" = top middle, "" = free):
    // there the corners are square and the bar sits flush against that side of its window
    property string edge: ""
    implicitWidth: (horizontal ? row.implicitWidth : col.implicitWidth) + 20
    implicitHeight: (horizontal ? row.implicitHeight : col.implicitHeight) + 12
    width: implicitWidth; height: implicitHeight
    // The overlay window only grows (resizing a window above a game every second costs the
    // game frames); the visible bar is always exactly as big as its content and sits at the
    // chosen side of that window. Before, the background filled the whole window and stayed
    // too wide after the numbers got shorter.
    readonly property real cx: edge === "right" ? width - implicitWidth
                             : edge === "center" ? Math.round((width - implicitWidth) / 2) : 0
    readonly property bool atTop: edge === "left" || edge === "right" || edge === "center"

    function esc(t) { return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") }
    function markup(g) {
        var lb = style.label_weight !== "normal", vb = style.weight !== "normal"
        var s = "<font color='" + g.color + "'>" + (lb ? "<b>" : "") + esc(g.name) + (lb ? "</b>" : "") + "</font>"
        for (var i = 0; i < g.items.length; ++i) {
            var it = g.items[i]
            s += "&nbsp;<font color='" + it.color + "'>" + (vb ? "<b>" : "") + esc(it.text) + (vb ? "</b>" : "") + "</font>"
        }
        return s
    }
    ListModel { id: lm }
    function sync() {
        var gs = (model && model.groups) ? model.groups : []
        var keep = {}
        for (var i = 0; i < gs.length; ++i) keep[gs[i].name] = true
        for (var r = lm.count - 1; r >= 0; --r) if (!keep[lm.get(r).name]) lm.remove(r)
        for (var k = 0; k < gs.length; ++k) {
            var h = markup(gs[k]), idx = -1
            for (var j = k; j < lm.count; ++j) if (lm.get(j).name === gs[k].name) { idx = j; break }
            if (idx < 0) lm.insert(k, {name: gs[k].name, html: h})
            else {
                if (idx !== k) { bar.reorder = true; settle.restart(); lm.move(idx, k, 1) }
                if (lm.get(k).html !== h) lm.setProperty(k, "html", h)
            }
        }
    }
    onModelChanged: sync()
    onStyleChanged: sync()
    Component.onCompleted: { sync(); Qt.callLater(function () { bar.checkUpright() }) }
    Timer { id: settle; interval: 450; onTriggered: bar.reorder = false }
    Transition { id: glide; NumberAnimation { properties: "x,y"; duration: 280; easing.type: Easing.OutCubic } }

    Rectangle {
        x: bar.cx; width: bar.implicitWidth; height: bar.implicitHeight
        topLeftRadius: bar.atTop || bar.edge === "left" ? 0 : 10
        topRightRadius: bar.atTop || bar.edge === "right" ? 0 : 10
        bottomLeftRadius: bar.edge === "left" ? 0 : 10
        bottomRightRadius: bar.edge === "right" ? 0 : 10
        color: Qt.rgba(Qt.color(style.bg_hex || "#101010").r,
                       Qt.color(style.bg_hex || "#101010").g,
                       Qt.color(style.bg_hex || "#101010").b, bar.bgAlpha)
        border.width: bar.glass ? 1 : 0
        border.color: Qt.rgba(1, 1, 1, 0.22)
    }
    Rectangle {                       // glass highlight
        visible: bar.glass
        x: bar.cx + 1; y: 1; width: bar.implicitWidth - 2; height: bar.implicitHeight - 2; radius: 9
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.14) }
            GradientStop { position: 0.55; color: Qt.rgba(1, 1, 1, 0.0) }
        }
    }

    Row {
        id: row
        visible: bar.horizontal
        x: bar.cx + 10; y: 6
        spacing: 10
        move: bar.reorder ? glide : null
        Repeater {
            model: lm
            Row {
                spacing: 10
                Text { visible: index > 0; text: "|"; color: Tokens.dim
                       font.family: style.font_resolved || "Consolas"; font.pixelSize: bar.px }
                Text { text: html; textFormat: Text.StyledText
                       font.family: style.font_resolved || "Consolas"; font.pixelSize: bar.px }
            }
        }
        Sparkline {
            visible: !!bar.model.graph && bar.model.graph.length > 1
            width: 120; height: bar.px + 6
            values: bar.model.graph || []
            // the scale follows the usual frame time (not the biggest spike), so it does not
            // jump up and down every time a slow frame comes or goes; spikes reach the top
            maxValue: { var v = (values || []).slice().sort(function (a, b) { return a - b })
                        return v.length ? Math.max(1, v[Math.floor(v.length / 2)] * 2.2) : 1 }
            slots: Math.max(2, values.length)
            slide: false
            color: Tokens.cyan
        }
    }
    Column {
        id: col
        visible: !bar.horizontal
        x: bar.cx + 10; y: 6
        spacing: 4
        move: bar.reorder ? glide : null
        Repeater {
            model: lm
            Text { text: html; textFormat: Text.StyledText
                   font.family: style.font_resolved || "Consolas"; font.pixelSize: bar.px }
        }
    }
}
