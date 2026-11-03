import QtQuick
import Lmonitor

// Shows the overlay bar over a colourful backdrop (so opacity and glass are
// visible) and scales it down when it is wider than the box.
Rectangle {
    id: root
    property var model: ({groups: [], graph: null})
    property var style: ({})
    radius: 10; clip: true
    border.width: 1; border.color: Tokens.line
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop { position: 0.0; color: "#1f3b5c" }
        GradientStop { position: 0.5; color: "#5a3d7a" }
        GradientStop { position: 1.0; color: "#7a4a3a" }
    }
    Rectangle { x: parent.width * 0.18; y: -parent.height * 0.3; width: parent.height * 1.4; height: width; radius: width / 2
                color: Qt.rgba(1, 1, 1, 0.10) }
    Rectangle { x: parent.width * 0.62; y: parent.height * 0.35; width: parent.height * 1.1; height: width; radius: width / 2
                color: Qt.rgba(1, 0.8, 0.4, 0.18) }
    OverlayBar {
        id: bar
        model: root.model; style: root.style
        transformOrigin: Item.TopLeft
        scale: implicitWidth > 0 ? Math.min(1, (root.width - 20) / implicitWidth) : 1
        x: 10; y: (root.height - implicitHeight * scale) / 2
    }
}
