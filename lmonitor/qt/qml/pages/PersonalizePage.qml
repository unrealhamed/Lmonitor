import QtQuick
import Lmonitor
import "../components"

// How Lmonitor looks: language, start with Windows, light or dark, accent color, size.
Item {
    id: page
    readonly property var s: backend.settings
    readonly property int g: Tokens.gap
    PageHeader {
        id: head; width: parent.width; kicker: Tr.t("Look and feel"); title: Tr.t("Personalize")
        Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Language"); color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Segmented { width: 200; model: ["English", "فارسی"]; index: page.s.language === "fa" ? 1 : 0
                    onPicked: function (i) { backend.setSetting("language", i === 1 ? "fa" : "en") } }
    }

    Column {
        y: head.height + 12; width: parent.width; spacing: page.g

        Card {                                          // ---- start with Windows
            width: parent.width; height: 78
            Text { x: 20; y: 18; text: Tr.t("Start with Windows"); color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
            Text { x: 20; y: 42; width: parent.width - 120; elide: Text.ElideRight
                   color: backend.autostartError !== "" ? Tokens.warn : Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 12
                   text: backend.autostartError !== "" ? Tr.t("Could not change it: ") + Tr.t(backend.autostartError)
                         : Tr.t("Lmonitor starts when you sign in and waits in the tray with the overlays ready.") }
            ToggleSwitch { anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter
                           checked: backend.autostart; onToggled: function (v) { backend.setAutostart(v) } }
        }

        Card {                                          // ---- light / dark
            width: parent.width; height: 254
            Text { x: 20; y: 18; text: Tr.t("Appearance"); color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
            Text { x: 20; y: 42; text: Tr.t("The same design in two modes. The in-game overlays always stay dark.")
                   color: Tokens.sub; font.family: Tokens.font; font.pixelSize: 12 }
            Row {
                x: 20; y: 72; width: parent.width - 40; spacing: page.g
                Repeater {
                    model: [{key: "light", name: "Light", icon: "", bg: "#F3F4F6", side: "#FFFFFF", card: "#FFFFFF",
                             line: "#E3E6EA", bar: "#047857", dimc: "#D2D7DE"},
                            {key: "dark", name: "Dark", icon: "", bg: "#0E1014", side: "#15181D", card: "#15181D",
                             line: "#252A32", bar: "#2DD4A0", dimc: "#333944"}]
                    Rectangle {
                        id: mode
                        readonly property bool on: page.s.ui_mode === modelData.key
                        width: (parent.width - page.g) / 2; height: 162; radius: 12
                        color: Tokens.bg0
                        border.width: on ? 2 : 1; border.color: on ? Tokens.accent : (modeMouse.containsMouse ? Tokens.lineStrong : Tokens.line)
                        Rectangle {                    // a small window in that mode
                            x: 10; y: 10; width: parent.width - 20; height: 108; radius: 8
                            color: modelData.bg; border.width: 1; border.color: modelData.line; clip: true
                            Rectangle { x: 1; y: 1; width: parent.width * 0.3; height: parent.height - 2; color: modelData.side
                                        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: modelData.line }
                                        Column { x: 10; y: 12; spacing: 7
                                                 Rectangle { width: 46; height: 6; radius: 3; color: modelData.bar }
                                                 Rectangle { width: 36; height: 5; radius: 3; color: modelData.dimc }
                                                 Rectangle { width: 42; height: 5; radius: 3; color: modelData.dimc } } }
                            Column { x: parent.width * 0.3 + 10; y: 10; width: parent.width * 0.7 - 20; spacing: 8
                                     Rectangle { width: parent.width; height: 40; radius: 6; color: modelData.card; border.width: 1; border.color: modelData.line }
                                     Rectangle { width: parent.width; height: 40; radius: 6; color: modelData.card; border.width: 1; border.color: modelData.line } }
                        }
                        Row { x: 14; y: 130; spacing: 8
                              Text { text: modelData.icon; color: Tokens.text; font.family: Tokens.iconFont; font.pixelSize: 15
                                     anchors.verticalCenter: parent.verticalCenter }
                              Text { text: Tr.t(modelData.name); color: Tokens.text; anchors.verticalCenter: parent.verticalCenter
                                     font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.weight: Font.DemiBold } }
                        Rectangle { anchors.right: parent.right; anchors.rightMargin: 14; y: 131; width: 18; height: 18; radius: 9
                                    color: "transparent"; border.width: 2; border.color: mode.on ? Tokens.accent : Tokens.lineStrong
                                    Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: Tokens.accent; visible: mode.on } }
                        MouseArea { id: modeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.setSetting("ui_mode", modelData.key) }
                    }
                }
            }
        }

        Row {
            width: parent.width; spacing: page.g
            Card {                                      // ---- accent
                width: (parent.width - page.g) / 2; height: 148
                Text { x: 20; y: 18; text: Tr.t("Accent color"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                Text { x: 20; y: 42; text: Tr.t("Used for switches, selections and main buttons."); color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: 12 }
                Row {
                    x: 20; y: 74; spacing: 14
                    Repeater {
                        model: backend.uiAccents
                        Column {
                            spacing: 6
                            readonly property bool on: page.s.ui_accent === modelData.key
                            Rectangle {
                                width: 36; height: 36; radius: 18; color: modelData.hex
                                border.width: parent.on ? 2 : 0; border.color: Tokens.card
                                Rectangle { anchors.fill: parent; anchors.margins: -3; radius: width / 2; color: "transparent"
                                            border.width: 2; border.color: Tokens.text; visible: parent.parent.on }
                                Text { anchors.centerIn: parent; visible: parent.parent.on; text: ""
                                       color: Tokens.accentText; font.family: Tokens.iconFont; font.pixelSize: 14 }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setSetting("ui_accent", modelData.key) }
                            }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: Tr.t(modelData.name)
                                   color: parent.on ? Tokens.text : Tokens.dim
                                   font.family: Tokens.font; font.pixelSize: 12 }
                        }
                    }
                }
            }
            Card {                                      // ---- interface size
                width: (parent.width - page.g) / 2; height: 148
                Text { x: 20; y: 18; text: Tr.t("Interface size"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                Text { x: 20; y: 42; text: Tr.t("Makes all text and controls bigger, for high-resolution screens.")
                       width: parent.width - 40; elide: Text.ElideRight
                       color: Tokens.sub; font.family: Tokens.font; font.pixelSize: 12 }
                Segmented { x: 20; y: 80; width: parent.width - 40
                            model: backend.uiScales.map(function (v) { return v + "%" })
                            index: backend.uiScales.indexOf(page.s.ui_scale)
                            onPicked: function (i) { backend.setSetting("ui_scale", backend.uiScales[i]) } }
            }
        }
    }
}
