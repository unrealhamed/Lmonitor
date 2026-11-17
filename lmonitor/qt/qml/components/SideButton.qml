import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// One item of the side menu: an icon (Windows' icon font) and the page name.
Rectangle {
    id: root
    property string label: ""
    property string icon: ""
    property bool active: false
    signal clicked()
    height: 36; radius: 8
    color: active ? Tokens.accentA(Tokens.light ? 0.10 : 0.13) : (hover.containsMouse ? Tokens.fg(0.05) : "transparent")
    Behavior on color { ColorAnimation { duration: 90 } }
    Text { x: 10; anchors.verticalCenter: parent.verticalCenter; width: 20; horizontalAlignment: Text.AlignHCenter
           text: root.icon; color: root.active ? Tokens.accent : Tokens.dim
           font.family: Tokens.iconFont; font.pixelSize: 16 }
    Text { anchors.verticalCenter: parent.verticalCenter; x: 40
           text: Tr.t(root.label); color: root.active ? Tokens.text : Tokens.sub
           font.family: Tokens.font; font.pixelSize: Tokens.fsBody + 1
           font.weight: root.active ? Font.DemiBold : Font.Medium }
    MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true
                cursorShape: Qt.PointingHandCursor; onClicked: root.clicked() }
}
