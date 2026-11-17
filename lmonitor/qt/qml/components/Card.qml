import QtQuick
import Lmonitor

// A flat panel with a hairline border. In light mode a very soft shadow lifts it off the
// grey background. (`accent` and `tint` are kept so older callers still work.)
Item {
    id: root
    property color accent: Tokens.accent
    property bool tint: false
    default property alias content: inner.data
    Rectangle {                                   // shadow (light mode only)
        visible: Tokens.light
        x: 0; y: 1; width: parent.width; height: parent.height
        radius: Tokens.radius; color: Qt.rgba(0.06, 0.09, 0.16, 0.06)
    }
    Rectangle {
        anchors.fill: parent
        radius: Tokens.radius
        color: Tokens.card
        border.width: 1; border.color: Tokens.line
    }
    Item { id: inner; anchors.fill: parent }
}
