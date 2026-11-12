import QtQuick
import Lmonitor
import "../components"

// Graph overlay settings. The preview is the same GraphHud the game shows, with the
// real numbers of the last minutes. Every control writes through backend.setSetting
// (validated by the engine) and is saved in settings.json.
Item {
    id: page
    readonly property var s: backend.settings
    property int n: 0                                   // which graph overlay: 0 / 1
    readonly property var h: backend.hudStyles[n] || ({})
    readonly property int g: Tokens.gap
    readonly property real colW: (width - g) / 2
    readonly property var items: h.hud_items || []
    readonly property var posKeys: ["tl", "tr", "bl", "br"]
    readonly property var windows: [0, 30, 60, 120, 300]

    // the preview reads the same data as the overlay (the backend reads it while this
    // page is open)
    Component.onCompleted: backend.setHudPageOpen(true)
    Component.onDestruction: backend.setHudPageOpen(false)

    PageHeader {
        id: head; width: parent.width
        kicker: Tr.t("Live charts over your game"); title: Tr.t("Graph overlay")
        Segmented { width: 220; anchors.verticalCenter: parent.verticalCenter
                    model: ["Graph 1", "Graph 2"]; index: page.n
                    onPicked: function (i) { page.n = i } }
        Text { text: page.h.hud_on ? Tr.t("On") : Tr.t("Off"); color: page.h.hud_on ? Tokens.accent : Tokens.dim
               anchors.verticalCenter: parent.verticalCenter
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
        ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: page.h.hud_on
                       onToggled: function (v) { backend.setHudSetting(page.n, "hud_on", v) } }
    }

    Card {                                         // live preview + move
        id: prev
        y: head.height + 12; width: parent.width; height: Math.min(420, Math.max(250, page.height * 0.44))
        Text { x: 20; y: 14; text: Tr.t("Live preview"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
        Text { anchors.right: parent.right; anchors.rightMargin: 20; y: 18; width: parent.width - 220
               horizontalAlignment: Text.AlignRight; elide: Text.ElideLeft
               text: Tr.t("It floats: drag it here, or grab its top edge on the screen")
               color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        Rectangle {                                 // a dark "game" behind the preview
            id: stage
            // the stage is a picture of the screen: it keeps left and right in Persian too
            property bool upright: false
            onUprightChanged: Tr.rev++
            function checkUpright() { stage.upright = Tr.rtl && stage.parent !== null && Tr.mirrored(stage.parent) }
            transform: Scale { origin.x: stage.width / 2; xScale: stage.upright ? -1 : 1 }
            Component.onCompleted: Qt.callLater(function () { stage.checkUpright() })
            Connections { target: Tr; function onLangChanged() { Qt.callLater(function () { stage.checkUpright() }) } }
            x: 16; y: 52; width: parent.width - 32; height: parent.height - 66; radius: 10; clip: true
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0.0; color: "#1b2433" }
                GradientStop { position: 0.55; color: "#2b2a3a" }
                GradientStop { position: 1.0; color: "#3a2a2a" }
            }
            Rectangle { x: parent.width * 0.1; y: parent.height * 0.55; width: parent.width * 0.5; height: parent.height
                        rotation: -8; color: Qt.rgba(1, 1, 1, 0.03) }
            Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10
                   text: Tr.t("Preview - real numbers from the last minutes"); color: Qt.rgba(1, 1, 1, 0.35)
                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
            GraphHud {
                id: demo
                info: backend.huds[page.n] || ({items: [], accent: "#35d6ff"})
                style: page.h
                animate: page.visible
                readonly property real fit: Math.min(1, (stage.width - 24) / implicitWidth,
                                                     (stage.height - 24) / implicitHeight)
                scale: fit
                transformOrigin: Item.TopLeft
                readonly property bool atLeft: page.h.hud_pos === "tl" || page.h.hud_pos === "bl"
                readonly property bool atTop: page.h.hud_pos !== "bl" && page.h.hud_pos !== "br"
                // custom place: shown at the same relative place of the stage
                readonly property real freeW: stage.width - 24 - implicitWidth * fit
                readonly property real freeH: stage.height - 24 - implicitHeight * fit
                readonly property bool custom: page.h.hud_pos === "custom"
                property bool dragging: false
                property real dragX: 0
                property real dragY: 0
                property point grabAt: Qt.point(0, 0)
                readonly property var rel: (backend.hudStates[page.n] || ({rel: {x: 1, y: 0}})).rel
                x: dragging ? dragX : custom ? 12 + freeW * rel.x : atLeft ? 12 : 12 + freeW
                y: dragging ? dragY : custom ? 12 + freeH * rel.y : atTop ? 12 : 12 + freeH
                MouseArea {                         // drag it here to place it on the screen
                    width: demo.implicitWidth; height: demo.implicitHeight
                    cursorShape: Qt.SizeAllCursor
                    onPressed: function (m) {
                        var p = mapToItem(stage, m.x, m.y)
                        demo.grabAt = Qt.point(p.x - demo.x, p.y - demo.y)
                        demo.dragX = demo.x; demo.dragY = demo.y; demo.dragging = true
                    }
                    onPositionChanged: function (m) {
                        if (!demo.dragging) return
                        var p = mapToItem(stage, m.x, m.y)
                        demo.dragX = Math.max(12, Math.min(12 + demo.freeW, p.x - demo.grabAt.x))
                        demo.dragY = Math.max(12, Math.min(12 + demo.freeH, p.y - demo.grabAt.y))
                    }
                    onReleased: {
                        backend.placeHud(page.n, demo.freeW > 0 ? (demo.dragX - 12) / demo.freeW : 0,
                                         demo.freeH > 0 ? (demo.dragY - 12) / demo.freeH : 0)
                        demo.dragging = false
                    }
                }
            }
        }
    }

    Flickable {
        id: flick
        y: prev.y + prev.height + page.g
        width: parent.width; height: parent.height - y
        contentWidth: width; contentHeight: Math.max(colA.height, colB.height) + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {                                   // ---- column A
            id: colA; width: page.colW; spacing: page.g
            Card {
                width: parent.width; height: chartsCol.height + 36
                Column {
                    id: chartsCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 12
                    Text { text: Tr.t("Charts"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.t("Pick up to 6. They are shown in the order you pick them. FPS and frame time need a game in front.") }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: backend.hudCatalog
                            Rectangle {
                                readonly property int pos: page.items.indexOf(modelData.key)
                                readonly property bool on: pos >= 0
                                readonly property bool full: !on && page.items.length >= backend.hudMaxItems
                                width: chipRow.width + 22; height: 32; radius: 10
                                opacity: full ? 0.45 : 1
                                color: on ? Tokens.accentA(0.20) : Tokens.fg(0.05)
                                border.width: 1; border.color: on ? Tokens.accent : Tokens.line
                                Row {
                                    id: chipRow; anchors.centerIn: parent; spacing: 6
                                    Text { visible: parent.parent.on; text: (parent.parent.pos + 1) + "."
                                           color: Tokens.accent; font.family: Tokens.font
                                           font.pixelSize: Tokens.fsSmall; font.bold: true }
                                    Text { text: Tr.t(modelData.title)
                                           color: parent.parent.on ? Tokens.text : Tokens.sub
                                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                                }
                                MouseArea { anchors.fill: parent; enabled: !parent.full
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setHudItem(page.n, modelData.key, !parent.on) }
                            }
                        }
                    }
                    Text { text: Tr.t("TIME SHOWN IN EACH CHART"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Real time", "30 s", "1 min", "2 min", "5 min"]
                                index: page.windows.indexOf(page.h.hud_window)
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_window", page.windows[i]) } }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: page.h.hud_window === 0
                                 ? Tr.t("Real time: the last 10 seconds, read 4 times a second. Frame time shows the worst frame of each moment, so stutters are easy to see.")
                                 : Tr.t("Each point is the average of its moment; the small numbers on the right are the real lowest and highest readings.") }
                    Text { text: Tr.t("MOTION"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Smooth", "Power saver"]
                                index: page.h.hud_motion === "saver" ? 1 : 0
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_motion", i === 1 ? "saver" : "smooth") } }
                }
            }
            Card {
                width: parent.width; height: posCol.height + 36
                Column {
                    id: posCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 12
                    Text { text: Tr.t("Position and visibility"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Top left", "Top right", "Bottom left", "Bottom right"]
                                index: page.posKeys.indexOf(page.h.hud_pos)
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_pos", page.posKeys[i]) } }
                    Segmented { width: parent.width
                                model: ["Always visible", "F10 shows / hides"]
                                index: page.h.hud_mode === "hotkey" ? 1 : 0
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_mode", i === 1 ? "hotkey" : "always") } }
                    Text { text: Tr.t("SHOW ON"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: ["primary"].concat(backend.screens)
                            Rectangle {
                                width: mon.width + 24; height: 32; radius: 10
                                color: page.h.hud_monitor === modelData ? Tokens.accentA(0.20) : Tokens.fg(0.05)
                                border.width: 1; border.color: page.h.hud_monitor === modelData ? Tokens.accent : Tokens.line
                                Text { id: mon; anchors.centerIn: parent
                                       text: modelData === "primary" ? Tr.t("Primary (Windows)") : modelData.replace("\\\\.\\", "")
                                       color: Tokens.text; font.family: Tokens.font
                                       font.pixelSize: Tokens.fsSmall; font.bold: true }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setHudSetting(page.n, "hud_monitor", modelData) }
                            }
                        }
                    }
                }
            }
        }

        Column {                                   // ---- column B
            id: colB; x: page.colW + page.g; width: page.colW; spacing: page.g
            Card {
                width: parent.width; height: lookCol.height + 36
                Column {
                    id: lookCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 12
                    Text { text: Tr.t("Look"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Gaming HUD", "Clean"]
                                index: page.h.hud_style === "clean" ? 1 : 0
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_style", i === 1 ? "clean" : "hud") } }
                    Text { text: Tr.t("COLOR THEME"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: backend.hudThemes
                            Rectangle {
                                readonly property bool on: page.h.hud_theme === modelData.key
                                width: themeRow.width + 20; height: 34; radius: 10
                                color: on ? Tokens.fg(0.10) : Tokens.fg(0.04)
                                border.width: on ? 2 : 1; border.color: on ? modelData.accent : Tokens.line
                                Row {
                                    id: themeRow; anchors.centerIn: parent; spacing: 4
                                    Repeater {
                                        model: modelData.colors.slice(0, 3)
                                        Rectangle { width: 10; height: 10; radius: 5; color: modelData
                                                    anchors.verticalCenter: parent.verticalCenter }
                                    }
                                    Item { width: 4; height: 1 }
                                    Text { text: Tr.t(modelData.name); color: Tokens.text
                                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                                }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setHudSetting(page.n, "hud_theme", modelData.key) }
                            }
                        }
                    }
                    Text { text: Tr.t("SIZE"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Small", "Medium", "Large"]
                                index: ["s", "m", "l"].indexOf(page.h.hud_size)
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_size", ["s", "m", "l"][i]) } }
                    Text { text: Tr.t("LAYOUT"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Column", "Row", "Grid"]
                                index: ["v", "h", "grid"].indexOf(page.h.hud_layout)
                                onPicked: function (i) { backend.setHudSetting(page.n, "hud_layout", ["v", "h", "grid"][i]) } }
                    SliderRow { width: parent.width; label: Tr.t("BACKGROUND OPACITY"); unit: "%"
                                from: 0; to: 100; step: 5; value: page.h.hud_alpha
                                onMoved: function (v) { backend.setHudSetting(page.n, "hud_alpha", v) } }
                }
            }
            Card {
                width: parent.width; height: costCol.height + 36
                Column {
                    id: costCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 8
                    Text { text: Tr.t("Made for gaming"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.t("The charts update once a second and do not animate in between, and the overlay never changes its size by itself. Mouse clicks go through it to the game.") }
                }
            }
            Pill { danger: true; label: Tr.t("Reset graph overlay settings"); onClicked: backend.resetHud(page.n) }
        }
    }
}
