import QtQuick
import Lmonitor
import "../components"

// How Lmonitor itself looks: app theme and accent color. Both are stored in the
// same settings file as the classic window (ui_theme / ui_accent).
Item {
    id: page
    readonly property var s: backend.settings
    PageHeader { id: head; width: parent.width; kicker: "Look and feel"; title: "Personalize" }

    Card {
        id: themes
        y: head.height + 12; width: Math.min(parent.width, 760)
        height: 62 + Math.ceil(backend.uiThemes.length / 2) * 150
        Text { x: 20; y: 18; text: "App theme"; color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
        Grid {
            x: 20; y: 54; columns: 2; spacing: 14
            Repeater {
                model: backend.uiThemes
                Item {
                    width: (themes.width - 54) / 2; height: 136
                    Rectangle {                              // mini window made from the theme's own colors
                        width: parent.width; height: 100; radius: 14
                        color: modelData.bg0
                        border.width: s.ui_theme === modelData.key ? 2 : 1
                        border.color: s.ui_theme === modelData.key ? Tokens.accent : modelData.line
                        Rectangle { x: 0; y: 0; width: 46; height: parent.height; radius: 14; color: modelData.bg1 }
                        Rectangle { x: 6; y: 12; width: 34; height: 6; radius: 3; color: modelData.accent }
                        Rectangle { x: 6; y: 26; width: 26; height: 5; radius: 2; color: modelData.dim }
                        Rectangle { x: 6; y: 38; width: 30; height: 5; radius: 2; color: modelData.dim }
                        Rectangle { x: 56; y: 12; width: parent.width - 68; height: 34; radius: 8; color: modelData.card
                                    border.width: 1; border.color: modelData.line
                                    Rectangle { x: 10; y: 10; width: 40; height: 6; radius: 3; color: modelData.text }
                                    Rectangle { x: 10; y: 21; width: 64; height: 5; radius: 2; color: modelData.sub } }
                        Rectangle { x: 56; y: 54; width: parent.width - 68; height: 34; radius: 8; color: modelData.card
                                    border.width: 1; border.color: modelData.line
                                    Rectangle { x: 10; y: 14; width: parent.width - 20; height: 6; radius: 3; color: modelData.line }
                                    Rectangle { x: 10; y: 14; width: (parent.width - 20) * 0.6; height: 6; radius: 3; color: modelData.accent } }
                    }
                    Text { y: 104; text: modelData.name; color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    Text { y: 121; width: parent.width; elide: Text.ElideRight; text: modelData.note; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: backend.setSetting("ui_theme", modelData.key) }
                }
            }
        }
    }

    Card {
        y: themes.y + themes.height + 14; width: themes.width; height: 150
        Text { x: 20; y: 18; text: "Accent color"; color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
        Row {
            x: 20; y: 54; spacing: 10
            Repeater {
                model: backend.uiAccents
                Rectangle {
                    width: 78; height: 42; radius: 12
                    color: modelData.hex !== "" ? modelData.hex : Tokens.fg(0.08)
                    border.width: s.ui_accent === modelData.key ? 3 : 1
                    border.color: s.ui_accent === modelData.key ? Tokens.text : Tokens.line
                    Text { anchors.centerIn: parent; text: modelData.name; font.bold: true
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           color: modelData.hex !== "" ? ((parseInt(modelData.hex.substr(1, 2), 16) * 0.299
                                  + parseInt(modelData.hex.substr(3, 2), 16) * 0.587
                                  + parseInt(modelData.hex.substr(5, 2), 16) * 0.114) > 140 ? "#10131a" : "#ffffff") : Tokens.text }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                onClicked: backend.setSetting("ui_accent", modelData.key) }
                }
            }
        }
        Text { x: 20; y: 108; width: parent.width - 40; wrapMode: Text.WordWrap; color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
               text: "Auto = the theme's own color. The same choice is used by the classic Lmonitor window." }
    }
}
