import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// Two-step button for anything that changes the PC: first click asks
// "Are you sure?", second click does it. Cancels itself after 6 seconds.
Item {
    id: root
    property string label: ""
    property string question: Tr.t("Are you sure?")
    property bool primary: false
    property bool danger: false
    property bool ready: true
    property bool asking: false
    signal confirmed()
    implicitWidth: asking ? askRow.width : pill.implicitWidth
    implicitHeight: 38
    opacity: ready ? 1 : 0.4
    Behavior on implicitWidth { NumberAnimation { duration: 120 } }
    Pill { id: pill; visible: !root.asking; label: root.label; primary: root.primary; danger: root.danger
           onClicked: if (root.ready) { root.asking = true; t.restart() } }
    Row {
        id: askRow; visible: root.asking; spacing: 8
        Text { anchors.verticalCenter: parent.verticalCenter; text: root.question; color: Tokens.warn
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
        Pill { label: Tr.t("Yes"); primary: true; height: 32; onClicked: { root.asking = false; t.stop(); root.confirmed() } }
        Pill { label: Tr.t("No"); height: 32; onClicked: { root.asking = false; t.stop() } }
    }
    Timer { id: t; interval: 6000; onTriggered: root.asking = false }
}
