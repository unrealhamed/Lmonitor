import QtQuick
import Lmonitor
import "../components"

// Overlay settings. Every control writes through backend.setSetting (engine
// validation) and is saved to settings.json. The preview is the same OverlayBar
// the game shows. Two balanced columns fill the page - no empty areas.
Item {
    id: page
    readonly property var s: backend.settings
    readonly property var posNames: ["left", "center", "right"]
    readonly property int g: Tokens.gap
    readonly property real colW: (width - g) / 2

    // "What the bar shows": groups sit at a y computed from the saved order,
    // so a changed order makes them glide (see Behavior on y below).
    readonly property var groupOrder: s.order ? s.order.groups : []
    property var groupHeights: ({})
    readonly property real groupGap: 14
    readonly property real groupTotal: {
        var t = 0
        for (var i = 0; i < groupOrder.length; ++i) t += (groupHeights[groupOrder[i]] || 0) + groupGap
        return Math.max(0, t - groupGap)
    }
    function groupOffset(name) {
        var pos = 0
        for (var i = 0; i < groupOrder.length; ++i) {
            if (groupOrder[i] === name) return pos
            pos += (groupHeights[groupOrder[i]] || 0) + groupGap
        }
        return pos
    }
    function groupSetH(name, h) {
        var m = {}
        for (var k in groupHeights) m[k] = groupHeights[k]
        m[name] = h
        groupHeights = m
    }

    PageHeader {
        id: head; width: parent.width
        kicker: Tr.t("Game bar"); title: Tr.t("Overlay")
        Text { text: page.s.on ? Tr.t("On") : Tr.t("Off"); color: page.s.on ? Tokens.accent : Tokens.dim
               anchors.verticalCenter: parent.verticalCenter
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
        ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: page.s.on
                       onToggled: function (v) { backend.setSetting("on", v) } }
    }

    Card {                                         // live preview + move
        id: prev
        y: head.height + 12; width: parent.width; height: 118; tint: true
        Text { x: 20; y: 14; text: Tr.t("Live preview"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 16; y: 10; spacing: 10
            Text { anchors.verticalCenter: parent.verticalCenter; width: 280
                   horizontalAlignment: Text.AlignRight; elide: Text.ElideLeft
                   text: backend.moving ? Tr.t("Drag the bar, then press Done") : Tr.t("Drag it anywhere - the position is saved")
                   color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
            Pill { primary: backend.moving; label: backend.moving ? Tr.t("Done") : Tr.t("Move with mouse")
                   onClicked: backend.setMoving(!backend.moving) }
        }
        FitBar { x: 16; y: 54; width: parent.width - 32; height: parent.height - 68
                 model: backend.overlay.groups.length > 0 ? backend.overlay : backend.preview
                 style: backend.settings }
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
                width: parent.width; height: 168
                Text { x: 20; y: 16; text: Tr.t("Density"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Segmented { x: 20; y: 50; width: parent.width - 40
                            model: ["Compact", Tr.t("Balanced"), Tr.t("Detailed")]
                            index: ["compact", "balanced", "detailed"].indexOf(backend.density)
                            onPicked: function (i) { backend.setDensity(["compact", "balanced", "detailed"][i]) } }
                Text { x: 20; y: 100; width: parent.width - 40; wrapMode: Text.WordWrap
                       color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                       text: ({compact: Tr.t("Compact: FPS and usage only."),
                               balanced: Tr.t("Balanced: usage, temperatures and FPS lows."),
                               detailed: Tr.t("Detailed: everything, plus the graph."),
                               "": Tr.t("Custom: you picked the metrics yourself (What the bar shows).")})[backend.density] || "" }
            }
            Card {
                width: parent.width; height: 214
                Text { x: 20; y: 16; text: Tr.t("Position and layout"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Segmented { x: 20; y: 52; width: parent.width - 40
                            model: ["Left", Tr.t("Center"), Tr.t("Right")]
                            index: page.posNames.indexOf(s.pos)
                            onPicked: function (i) { backend.setSetting("pos", page.posNames[i]) } }
                Segmented { x: 20; y: 100; width: parent.width - 40
                            model: ["Horizontal", Tr.t("Vertical")]
                            index: s.layout === "v" ? 1 : 0
                            onPicked: function (i) { backend.setSetting("layout", i === 1 ? "v" : "h") } }
                SliderRow { x: 20; y: 150; width: parent.width - 40; label: Tr.t("TEXT SIZE"); unit: " pt"
                            from: 8; to: 18; step: 1; value: s.text
                            onMoved: function (v) { backend.setSetting("text", v) } }
            }
            Card {
                width: parent.width; height: apCol.height + 36
                Column {
                    id: apCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 14
                    Text { text: Tr.t("Appearance"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Dark transparent", Tr.t("Liquid glass")]
                                index: s.look === "glass" ? 1 : 0
                                onPicked: function (i) { backend.setSetting("look", i === 1 ? "glass" : "dark") } }
                    Text { visible: s.look === "glass"; width: parent.width; wrapMode: Text.WordWrap
                           text: backend.glassOk ? Tr.t("Glass blurs the game behind the bar (visible in the game, not in this preview).")
                                                 : Tr.t("Windows blur is not available - a translucent bar is used.")
                           color: backend.glassOk ? Tokens.dim : Tokens.warn
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    SliderRow { width: parent.width; label: Tr.t("OPACITY"); unit: "%"
                                from: 40; to: 100; step: 5; value: s.alpha
                                onMoved: function (v) { backend.setSetting("alpha", v) } }
                    Text { text: Tr.t("BACKGROUND"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: backend.backgrounds
                            Rectangle {
                                width: 44; height: 30; radius: 8; color: modelData.hex
                                border.width: s.bg === modelData.key ? 2 : 1
                                border.color: s.bg === modelData.key ? Tokens.accent : Tokens.line
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setSetting("bg", modelData.key) }
                            }
                        }
                    }
                    Text { text: Tr.t("VALUE COLOR"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: backend.valueColors
                            Rectangle {
                                width: 30; height: 30; radius: 15; color: modelData.hex
                                border.width: s.value_color === modelData.key ? 3 : 0
                                border.color: "white"
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setSetting("value_color", modelData.key) }
                            }
                        }
                    }
                    Row {
                        width: parent.width; spacing: 16
                        Column {
                            width: (parent.width - 16) / 2; spacing: 8
                            Text { text: Tr.t("VALUES"); color: Tokens.sub
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                            Segmented { width: parent.width; model: ["Regular", Tr.t("Bold")]; index: s.weight === "bold" ? 1 : 0
                                        onPicked: function (i) { backend.setSetting("weight", i === 1 ? "bold" : "normal") } }
                        }
                        Column {
                            width: (parent.width - 16) / 2; spacing: 8
                            Text { text: Tr.t("LABELS"); color: Tokens.sub
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                            Segmented { width: parent.width; model: ["Regular", Tr.t("Bold")]; index: s.label_weight === "bold" ? 1 : 0
                                        onPicked: function (i) { backend.setSetting("label_weight", i === 1 ? "bold" : "normal") } }
                        }
                    }
                }
            }
        }

        Column {                                   // ---- column B
            id: colB; x: page.colW + page.g; width: page.colW; spacing: page.g
            Card {
                width: parent.width; height: 70 + page.groupTotal
                Text { x: 20; y: 16; text: Tr.t("What the bar shows"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                Item {
                    id: grp
                    x: 20; y: 52; width: parent.width - 40; height: page.groupTotal
                    Repeater {
                        model: backend.groups
                        Column {
                            id: grpCol
                            width: grp.width; spacing: 8
                            y: page.groupOffset(modelData.name)
                            Behavior on y { NumberAnimation { duration: 300; easing.type: Easing.OutCubic } }
                            onHeightChanged: page.groupSetH(modelData.name, height)
                            Component.onCompleted: page.groupSetH(modelData.name, height)
                            Row {
                                spacing: 10
                                Text { text: modelData.name.toUpperCase(); color: Tokens.accent
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                                Text { text: "▲"; color: Tokens.sub
                                       MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor
                                                   onClicked: backend.moveGroup(modelData.name, -1) } }
                                Text { text: "▼"; color: Tokens.sub
                                       MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor
                                                   onClicked: backend.moveGroup(modelData.name, 1) } }
                            }
                            Flow {
                                width: parent.width; spacing: 8
                                Repeater {
                                    model: modelData.items
                                    Rectangle {
                                        width: lab.width + 24; height: 30; radius: 10
                                        color: s.show[modelData.key] ? Tokens.accentA(0.20) : Tokens.fg(0.05)
                                        border.width: 1
                                        border.color: s.show[modelData.key] ? Tokens.accent : Tokens.line
                                        Text { id: lab; anchors.centerIn: parent; text: Tr.t(modelData.label)
                                               color: s.show[modelData.key] ? Tokens.text : Tokens.dim
                                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                    onClicked: backend.setShow(modelData.key, !s.show[modelData.key]) }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Card {
                width: parent.width; height: vCol.height + 36
                Column {
                    id: vCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 14
                    Text { text: Tr.t("When is the bar visible"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Always visible", Tr.t("F9 slides it in")]
                                index: s.show_mode === "hotkey" ? 1 : 0
                                onPicked: function (i) { backend.setSetting("show_mode", i === 1 ? "hotkey" : "always") } }
                    Text { text: Tr.t("STAY ON SCREEN AFTER F9"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Item {
                        width: parent.width; height: 36
                        Segmented { width: 200; model: ["3 s", "5 s", "10 s"]; index: [3, 5, 10].indexOf(s.hotkey_secs)
                                    onPicked: function (i) { backend.setSetting("hotkey_secs", [3, 5, 10][i]) } }
                        Pill { anchors.right: parent.right; label: Tr.t("Try it now"); onClicked: backend.tryReveal() }
                    }
                    Text { text: Tr.t("SHOW ON"); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                    Flow {
                        width: parent.width; spacing: 8
                        Repeater {
                            model: ["primary"].concat(backend.screens)
                            Rectangle {
                                width: chip.width + 24; height: 32; radius: 10
                                color: s.monitor === modelData ? Tokens.accentA(0.20) : Tokens.fg(0.05)
                                border.width: 1; border.color: s.monitor === modelData ? Tokens.accent : Tokens.line
                                Text { id: chip; anchors.centerIn: parent
                                       text: modelData === "primary" ? Tr.t("Primary (Windows)") : modelData.replace("\\\\.\\", "")
                                       color: Tokens.text; font.family: Tokens.font
                                       font.pixelSize: Tokens.fsSmall; font.bold: true }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setSetting("monitor", modelData) }
                            }
                        }
                    }
                }
            }
            Pill { danger: true; label: Tr.t("Reset overlay settings"); onClicked: backend.resetSettings() }
        }
    }
}
