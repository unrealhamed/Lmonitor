import QtQuick
import QtQuick.Window
import Lmonitor
import "."                      // components/Text.qml

// "What's new": a box in the middle of the window, shown once after an update that added
// something (Main.qml blurs the window behind it). One slide per change, each with a small
// moving picture. info: {version, since, slides: [{art, kind, title, text}]}
Item {
    id: wn
    property var info: ({})
    property bool open: false
    signal closed()
    readonly property var slides: info && info.slides ? info.slides : []
    property int at: 0
    readonly property var cur: slides[at] || ({})
    readonly property bool last: at >= slides.length - 1
    visible: opacity > 0
    opacity: open ? 1 : 0
    Behavior on opacity { NumberAnimation { duration: 220 } }
    onOpenChanged: if (open) { at = 0; takeKeys() }
    // the arrow keys, Enter and Esc work at once - also when the box is open from the start
    // (onOpenChanged does not run then) and after a click somewhere on it
    function takeKeys() { Qt.callLater(function () { if (wn.open) card.forceActiveFocus() }) }
    Component.onCompleted: if (open) takeKeys()
    Connections { target: wn.Window.window; function onActiveChanged() { if (wn.open) wn.takeKeys() } }

    function next() { if (last) closed(); else { dir = 1; at += 1 } }
    function back() { if (at > 0) { dir = -1; at -= 1 } }
    property int dir: 1

    Rectangle { anchors.fill: parent; color: Qt.rgba(0, 0, 0, 0.45) }
    MouseArea { anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.AllButtons
                onPressed: wn.takeKeys()
                onWheel: function (w) { w.accepted = true } }      // nothing behind can be clicked

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(parent.width - 60, 680); height: Math.min(parent.height - 60, 500)
        radius: Tokens.radius + 4; color: Tokens.card
        border.width: 1; border.color: Tokens.accentA(0.55)
        scale: wn.open ? 1 : 0.94
        Behavior on scale { NumberAnimation { duration: 260; easing.type: Easing.OutBack } }
        focus: true
        Keys.onEscapePressed: wn.closed()
        Keys.onRightPressed: wn.next()
        Keys.onLeftPressed: wn.back()
        Keys.onReturnPressed: wn.next()
        Keys.onEnterPressed: wn.next()
        Keys.onSpacePressed: wn.next()

        Rectangle {                                // soft accent glow at the top
            anchors.fill: parent; anchors.margins: 1; radius: parent.radius - 1
            gradient: Gradient { GradientStop { position: 0.0; color: Tokens.accentA(0.14) }
                                 GradientStop { position: 0.45; color: "transparent" } }
        }
        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 22
               text: Tr.t("What's new in Lmonitor"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 22; font.bold: true }
        Text { anchors.horizontalCenter: parent.horizontalCenter; y: 54; color: Tokens.sub
               text: Tr.line(Tr.t("Version ") + (wn.info.version || "") + "  ·  " + Tr.t("since ") + (wn.info.since || ""))
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Pill { anchors.right: parent.right; anchors.rightMargin: 16; y: 16; height: 32
               label: Tr.t("Skip"); onClicked: wn.closed() }

        // ---- the slide (made again for every step, so it comes in with a small move)
        Item {
            id: stageBox
            x: 30; y: 84; width: parent.width - 60; height: parent.height - 84 - 78
            Repeater {
                model: wn.slides.length
                Item {
                    id: slide
                    readonly property var s: wn.slides[index] || ({})
                    readonly property bool on: index === wn.at && wn.open
                    anchors.fill: parent
                    opacity: on ? 1 : 0
                    visible: opacity > 0
                    transform: Translate { x: slide.on ? 0 : (index < wn.at ? -40 : 40)
                                           Behavior on x { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } } }
                    Behavior on opacity { NumberAnimation { duration: 240 } }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter; y: 0
                        width: 360; height: 176; radius: 14; color: Tokens.fg(0.035)
                        border.width: 1; border.color: Tokens.line
                        WhatsNewArt { anchors.fill: parent; kind: slide.s.art || ""; running: slide.on }
                    }
                    Rectangle {
                        id: tag
                        anchors.horizontalCenter: parent.horizontalCenter; y: 190
                        width: tagText.implicitWidth + 22; height: 22; radius: 11
                        color: slide.s.kind === "fix" ? Qt.rgba(0.38, 0.78, 1, 0.16) : Tokens.accentA(0.18)
                        Text { id: tagText; anchors.centerIn: parent
                               text: Tr.t(slide.s.kind === "fix" ? "Fixed" : "New")
                               color: slide.s.kind === "fix" ? Tokens.cyan : Tokens.accent
                               font.family: Tokens.font; font.pixelSize: 11; font.bold: true }
                    }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; y: 220; width: parent.width
                           horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight
                           text: Tr.t(slide.s.title || ""); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 22; font.bold: true }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; y: 256; width: Math.min(parent.width, 520)
                           horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; lineHeight: 1.2
                           text: Tr.t(slide.s.text || ""); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: 14 }
                }
            }
        }

        // ---- steps and buttons
        Row {
            anchors.horizontalCenter: parent.horizontalCenter; y: parent.height - 34; spacing: 7
            Repeater {
                model: wn.slides.length
                Rectangle { width: index === wn.at ? 22 : 8; height: 8; radius: 4
                            color: index === wn.at ? Tokens.accent : Tokens.fg(0.2)
                            Behavior on width { NumberAnimation { duration: 180 } }
                            MouseArea { anchors.fill: parent; anchors.margins: -5; cursorShape: Qt.PointingHandCursor
                                        onClicked: wn.at = index } }
            }
        }
        Pill { x: 20; y: parent.height - 58; visible: wn.at > 0; label: Tr.t("Back"); onClicked: wn.back() }
        Pill { anchors.right: parent.right; anchors.rightMargin: 20; y: parent.height - 58; primary: true
               label: wn.last ? Tr.t("Got it") : Tr.t("Next"); onClicked: wn.next() }
    }
}
