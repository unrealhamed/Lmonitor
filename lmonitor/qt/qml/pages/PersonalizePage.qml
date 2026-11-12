import QtQuick
import Lmonitor
import "../components"

// How Lmonitor itself looks: language, size, corners, font, app theme and accent color.
Item {
    id: page
    readonly property var s: backend.settings
    readonly property int g: Tokens.gap
    function onDark(hex) {              // readable text color on a swatch
        return (parseInt(hex.substr(1, 2), 16) * 0.299 + parseInt(hex.substr(3, 2), 16) * 0.587
                + parseInt(hex.substr(5, 2), 16) * 0.114) > 140 ? "#10131a" : "#ffffff"
    }
    PageHeader {
        id: head; width: parent.width; kicker: Tr.t("Look and feel"); title: Tr.t("Personalize")
        Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Language"); color: Tokens.sub
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Segmented { width: 200; model: ["English", "فارسی"]; index: page.s.language === "fa" ? 1 : 0
                    onPicked: function (i) { backend.setSetting("language", i === 1 ? "fa" : "en") } }
    }

    Flickable {
        y: head.height + 12; width: parent.width; height: parent.height - y
        contentWidth: width; contentHeight: col.height + 8; clip: true; boundsBehavior: Flickable.StopAtBounds
        Column {
            id: col; width: parent.width; spacing: page.g

            Card {                                          // ---- start with Windows
                width: parent.width; height: 96
                Text { x: 20; y: 16; text: Tr.t("Start with Windows"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Text { x: 20; y: 44; width: parent.width - 120; wrapMode: Text.WordWrap
                       color: backend.autostartError !== "" ? Tokens.warn : Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                       text: backend.autostartError !== "" ? Tr.t("Could not change it: ") + Tr.t(backend.autostartError)
                             : Tr.t("Lmonitor starts by itself when you sign in to Windows and waits in the tray next to the clock, with the overlays ready. No question from Windows each time.") }
                ToggleSwitch { anchors.right: parent.right; anchors.rightMargin: 20; y: 20; checked: backend.autostart
                               onToggled: function (v) { backend.setAutostart(v) } }
            }

            Card {                                          // ---- size, corners, font
                width: parent.width; height: 196
                Text { x: 20; y: 16; text: Tr.t("Window"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Row {
                    x: 20; y: 52; width: parent.width - 40; spacing: 20
                    Column {
                        width: (parent.width - 40) / 3; spacing: 8
                        Text { text: Tr.t("INTERFACE AND TEXT SIZE"); color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                        Segmented { width: parent.width
                                    model: backend.uiScales.map(function (v) { return v + "%" })
                                    index: backend.uiScales.indexOf(page.s.ui_scale)
                                    onPicked: function (i) { backend.setSetting("ui_scale", backend.uiScales[i]) } }
                        Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                               text: Tr.t("Makes all text and controls bigger or smaller.") }
                    }
                    Column {
                        width: (parent.width - 40) / 3; spacing: 8
                        Text { text: Tr.t("CORNERS"); color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                        Segmented { width: parent.width; model: ["Sharp", "Soft", "Round"]
                                    index: ["sharp", "soft", "round"].indexOf(page.s.ui_radius)
                                    onPicked: function (i) { backend.setSetting("ui_radius", ["sharp", "soft", "round"][i]) } }
                    }
                    Column {
                        width: (parent.width - 40) / 3; spacing: 8
                        Text { text: Tr.t("FONT"); color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                        Flow {
                            width: parent.width; spacing: 6
                            Repeater {
                                model: backend.uiFonts
                                Rectangle {
                                    readonly property bool on: page.s.ui_font === modelData
                                    width: fl.width + 20; height: 30; radius: 9
                                    color: on ? Tokens.accentA(0.20) : Tokens.fg(0.05)
                                    border.width: 1; border.color: on ? Tokens.accent : Tokens.line
                                    Text { id: fl; anchors.centerIn: parent; text: modelData; color: Tokens.text
                                           font.family: modelData; font.pixelSize: Tokens.fsBody }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                onClicked: backend.setSetting("ui_font", modelData) }
                                }
                            }
                        }
                    }
                }
            }

            Card {                                          // ---- themes
                id: themes
                readonly property int cols: width > 1000 ? 5 : width > 760 ? 4 : 3
                readonly property real tileW: (width - 40 - (cols - 1) * 14) / cols
                width: parent.width
                height: 62 + Math.ceil(backend.uiThemes.length / cols) * 132
                Text { x: 20; y: 16; text: Tr.t("App theme"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Grid {
                    x: 20; y: 52; columns: themes.cols; spacing: 14
                    Repeater {
                        model: backend.uiThemes
                        Item {
                            width: themes.tileW; height: 118
                            Rectangle {                      // mini window made from the theme's own colors
                                width: parent.width; height: 78; radius: 12
                                color: modelData.bg0
                                border.width: s.ui_theme === modelData.key ? 2 : 1
                                border.color: s.ui_theme === modelData.key ? Tokens.accent : modelData.line
                                Rectangle { x: 1; y: 1; width: 38; height: parent.height - 2; radius: 11; color: modelData.bg1 }
                                Rectangle { x: 7; y: 12; width: 26; height: 5; radius: 3; color: modelData.accent }
                                Rectangle { x: 7; y: 24; width: 20; height: 4; radius: 2; color: modelData.dim }
                                Rectangle { x: 7; y: 34; width: 24; height: 4; radius: 2; color: modelData.dim }
                                Rectangle { x: 48; y: 10; width: parent.width - 58; height: 26; radius: 7; color: modelData.card
                                            border.width: 1; border.color: modelData.line
                                            Rectangle { x: 8; y: 7; width: 34; height: 5; radius: 3; color: modelData.text }
                                            Rectangle { x: 8; y: 16; width: 50; height: 4; radius: 2; color: modelData.sub } }
                                Rectangle { x: 48; y: 42; width: parent.width - 58; height: 26; radius: 7; color: modelData.card
                                            border.width: 1; border.color: modelData.line
                                            Rectangle { x: 8; y: 10; width: parent.width - 16; height: 5; radius: 3; color: modelData.line }
                                            Rectangle { x: 8; y: 10; width: (parent.width - 16) * 0.6; height: 5; radius: 3; color: modelData.accent } }
                            }
                            Text { y: 82; text: Tr.t(modelData.name); color: Tokens.text
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                            Text { y: 99; width: parent.width; elide: Text.ElideRight; text: Tr.t(modelData.note); color: Tokens.dim
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                        onClicked: backend.setSetting("ui_theme", modelData.key) }
                        }
                    }
                }
            }

            Card {                                          // ---- accent
                width: parent.width; height: acc.height + 70
                Text { x: 20; y: 16; text: Tr.t("Accent color"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Column {
                    id: acc
                    x: 20; y: 52; width: parent.width - 40; spacing: 12
                    Flow {
                        width: parent.width; spacing: 10
                        Repeater {
                            model: backend.uiAccents
                            Rectangle {
                                readonly property string hex: modelData.key === "custom" ? backend.hueHex(page.s.ui_hue) : modelData.hex
                                width: 78; height: 40; radius: 12
                                color: hex !== "" ? hex : Tokens.fg(0.08)
                                border.width: s.ui_accent === modelData.key ? 3 : 1
                                border.color: s.ui_accent === modelData.key ? Tokens.text : Tokens.line
                                Text { anchors.centerIn: parent; text: Tr.t(modelData.name); font.bold: true
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                                       color: parent.hex !== "" ? page.onDark(parent.hex) : Tokens.text }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setSetting("ui_accent", modelData.key) }
                            }
                        }
                    }
                    Item {                                   // custom: any hue
                        width: Math.min(parent.width, 560); height: 44
                        Text { text: Tr.t("YOUR OWN COLOR"); color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                        Rectangle {
                            id: hueBar
                            y: 22; width: parent.width; height: 14; radius: 7
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.000; color: backend.hueHex(0) }
                                GradientStop { position: 0.167; color: backend.hueHex(60) }
                                GradientStop { position: 0.333; color: backend.hueHex(120) }
                                GradientStop { position: 0.500; color: backend.hueHex(180) }
                                GradientStop { position: 0.667; color: backend.hueHex(240) }
                                GradientStop { position: 0.833; color: backend.hueHex(300) }
                                GradientStop { position: 1.000; color: backend.hueHex(359) }
                            }
                            Rectangle { width: 20; height: 20; radius: 10; y: -3; color: backend.hueHex(page.s.ui_hue)
                                        border.width: 3; border.color: "white"
                                        x: page.s.ui_hue / 359 * (hueBar.width - width) }
                            MouseArea {
                                anchors.fill: parent; anchors.margins: -8
                                function pick(mx) {
                                    var h = Math.round(Math.max(0, Math.min(1, (mx - 8) / hueBar.width)) * 359)
                                    if (h !== page.s.ui_hue) backend.setSetting("ui_hue", h)
                                    if (page.s.ui_accent !== "custom") backend.setSetting("ui_accent", "custom")
                                }
                                onPressed: function (m) { pick(m.x) }
                                onPositionChanged: function (m) { if (pressed) pick(m.x) }
                            }
                        }
                    }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.t("Auto = the theme's own color.") }
                }
            }
        }
    }
}
