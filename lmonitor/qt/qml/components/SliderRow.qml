import QtQuick
import Lmonitor

// Label + value + slider, all custom (no style dependency).
Item {
    id: root
    property string label: ""
    property real from: 0
    property real to: 100
    property real step: 1
    property real value: 0
    property string unit: ""
    signal moved(real v)
    height: 44
    Text { x: 0; y: 0; text: root.label; color: Tokens.sub
           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
    Text { anchors.right: parent.right; y: 0; text: Math.round(root.value) + root.unit
           color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
    Rectangle {
        id: track
        y: 28; width: parent.width; height: 6; radius: 3; color: Tokens.fg(0.12)
        Rectangle { width: knob.x + knob.width / 2; height: parent.height; radius: 3; color: Tokens.accent }
        Rectangle {
            id: knob; width: 18; height: 18; radius: 9; y: -6; color: "white"
            x: (root.value - root.from) / (root.to - root.from) * (track.width - width)
        }
        MouseArea {
            anchors.fill: parent; anchors.topMargin: -10; anchors.bottomMargin: -10
            function setFrom(mx) {
                var f = Math.max(0, Math.min(1, (mx - knob.width / 2) / (track.width - knob.width)))
                var v = root.from + f * (root.to - root.from)
                v = Math.round(v / root.step) * root.step
                if (v !== root.value) root.moved(v)
            }
            onPressed: function (m) { setFrom(m.x) }
            onPositionChanged: function (m) { if (pressed) setFrom(m.x) }
        }
    }
}
