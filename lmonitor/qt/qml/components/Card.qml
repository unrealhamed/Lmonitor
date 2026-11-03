import QtQuick
import Lmonitor

// Flat dark panel with a hairline border (the look of the reference design).
// `accent` is kept so older callers still work; it only tints the border a little.
Item {
    id: root
    property color accent: Tokens.accent
    property bool tint: false         // faint accent glow in the lower right corner
    default property alias content: inner.data
    Rectangle {
        anchors.fill: parent
        radius: Tokens.radius
        border.width: 1
        border.color: Tokens.line
        gradient: Gradient {
            GradientStop { position: 0.0; color: Tokens.cardHi }
            GradientStop { position: 1.0; color: Tokens.card }
        }
    }
    Rectangle {
        visible: root.tint
        anchors.fill: parent; anchors.margins: 1
        radius: Tokens.radius
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.10) }
        }
    }
    Item { id: inner; anchors.fill: parent }
}
