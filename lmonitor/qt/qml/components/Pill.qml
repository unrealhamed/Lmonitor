import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Button. primary = filled with the accent; danger = red text; otherwise a quiet button.
// States: hover, pressed, disabled (enabled: false).
Rectangle {
    id: root
    property string label: ""
    property bool primary: false
    property bool danger: false
    signal clicked()
    implicitWidth: txt.implicitWidth + 30
    height: 36; radius: 8
    opacity: enabled ? 1 : 0.45
    color: primary ? (ma.pressed ? Tokens.accent : ma.containsMouse ? Tokens.accentHover : Tokens.accent)
         : danger ? (ma.containsMouse ? Tokens.tint(Tokens.danger, 0.10) : "transparent")
         : (ma.pressed ? Tokens.fg(0.10) : ma.containsMouse ? (Tokens.light ? Tokens.bg0 : Tokens.fg(0.08))
            : (Tokens.light ? Tokens.card : Tokens.raised))
    border.width: primary ? 0 : 1
    border.color: danger ? Tokens.tint(Tokens.danger, 0.45) : Tokens.lineStrong
    Behavior on color { ColorAnimation { duration: 90 } }
    Text { id: txt; anchors.centerIn: parent; text: Tr.t(root.label)
           color: root.primary ? Tokens.accentText : root.danger ? Tokens.danger : Tokens.text
           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.weight: Font.DemiBold }
    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; enabled: root.enabled
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
