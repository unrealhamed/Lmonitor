import QtQuick
import Lmonitor

// Area chart with grid and y labels. maxValue > 0 fixes the scale
// (e.g. 100 for %); 0 = scale to the data.
Item {
    id: root
    property var values: []
    property color color: Tokens.cyan
    property real maxValue: 100
    property string unit: ""
    property int slots: 60
    readonly property real scaleMax: {
        if (maxValue > 0) return maxValue
        var m = 0, v = values || []
        for (var i = 0; i < v.length; ++i) if (v[i] !== null && v[i] !== undefined && v[i] > m) m = v[i]
        return m > 0 ? m * 1.2 : 1
    }
    function lab(f) { var x = scaleMax * f; return (maxValue > 0 || x >= 100 ? Math.round(x) : x.toFixed(1)) + root.unit }
    Repeater {
        model: [1, 0.5, 0]
        Text { x: 0; y: root.height * index / 2 - 7; width: 38
               text: root.lab(modelData); color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: 10 }
    }
    Repeater {
        model: 3
        Rectangle { x: 44; width: root.width - 44; height: 1; color: "#26262c"
                    y: Math.min(root.height - 1, Math.round(root.height * index / 2)) }
    }
    LiveCanvas {
        x: 44; width: parent.width - 44; height: parent.height
        series: [root.values]; colors: [root.color]
        maxValue: root.scaleMax; slots: root.slots
        interval: backend.interval
    }
}
