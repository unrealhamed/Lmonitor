import QtQuick
import Lmonitor

// Small area chart (cards, network, overlay graph). values: oldest first.
LiveCanvas {
    id: c
    property var values: []
    property color color: Tokens.cyan
    series: [values]
    colors: [color]
    interval: backend.interval
}
