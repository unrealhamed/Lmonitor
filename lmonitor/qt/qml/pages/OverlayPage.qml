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
                width: parent.width; height: 132
                Text { x: 20; y: 18; text: Tr.t("Appearance"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                Text { x: 20; y: 42; width: parent.width - 40; elide: Text.ElideRight
                       text: Tr.t("A dark, see-through bar that stays readable over any game.")
                       color: Tokens.sub; font.family: Tokens.font; font.pixelSize: 12 }
                SliderRow { x: 20; y: 72; width: parent.width - 40; label: Tr.t("OPACITY"); unit: "%"
                            from: 40; to: 100; step: 5; value: s.alpha
                            onMoved: function (v) { backend.setSetting("alpha", v) } }
            }
            Card {                                 // every game keeps its own overlay settings
                id: profCard
                readonly property var gp: backend.gameProfile
                width: parent.width; height: profCol.height + 36
                Column {
                    id: profCol; x: 20; y: 16; width: parent.width - 40; spacing: 10
                    Item { width: parent.width; height: 24
                        Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 60; elide: Text.ElideRight
                               text: Tr.t("Settings for each game"); color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                        ToggleSwitch { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                       checked: profCard.gp.on === true
                                       onToggled: function (v) { backend.setSetting("profiles_on", v) } } }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: !profCard.gp.on ? Tr.t("Off: every game uses the same overlay settings.")
                                 : profCard.gp.game ? Tr.line(Tr.t("Playing now: ") + profCard.gp.game + Tr.t(". Changes you make now are kept for this game only."))
                                 : Tr.t("Change the overlays while a game runs and that game keeps those settings. Other games use the normal ones.") }
                    Text { visible: profCard.gp.on === true && profCard.gp.count > 0; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.line(profCard.gp.count + Tr.t(" game(s) have their own settings")) }
                    Pill { visible: profCard.gp.has_own === true; label: Tr.t("Use the normal settings for this game")
                           onClicked: backend.forgetGameProfile() }
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
                                        color: s.show[modelData.key] ? Tokens.accentA(Tokens.light ? 0.12 : 0.16) : Tokens.bg0
                                        border.width: 1
                                        border.color: s.show[modelData.key] ? Tokens.accentA(0.0) : Tokens.line
                                        Row { id: lab; anchors.centerIn: parent; spacing: 5
                                              Text { visible: s.show[modelData.key]; text: "\uE73E"; color: Tokens.accent
                                                     anchors.verticalCenter: parent.verticalCenter
                                                     font.family: Tokens.iconFont; font.pixelSize: 10 }
                                              Text { text: Tr.t(modelData.label)
                                                     color: s.show[modelData.key] ? Tokens.accent : Tokens.sub
                                                     font.family: Tokens.font; font.pixelSize: 12; font.weight: Font.DemiBold } }
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
                                color: s.monitor === modelData ? Tokens.accentA(Tokens.light ? 0.12 : 0.16) : Tokens.bg0
                                border.width: 1; border.color: s.monitor === modelData ? Tokens.accentA(0.0) : Tokens.line
                                Text { id: chip; anchors.centerIn: parent
                                       text: modelData === "primary" ? Tr.t("Primary (Windows)") : modelData.replace("\\\\.\\", "")
                                       color: s.monitor === modelData ? Tokens.accent : Tokens.sub; font.family: Tokens.font
                                       font.pixelSize: Tokens.fsSmall; font.bold: true }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: backend.setSetting("monitor", modelData) }
                            }
                        }
                    }
                }
            }
            Card {                                 // anti-cheat safe mode
                width: parent.width; height: safeCol.height + 36
                readonly property var safe: backend.dashboard.safe || ({active: false, game: ""})
                id: safeCard
                Column {
                    id: safeCol
                    x: 20; y: 16; width: parent.width - 40; spacing: 12
                    Text { text: Tr.t("Anti-cheat safe mode"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Segmented { width: parent.width
                                model: ["Automatic", "Always on", "Off"]
                                index: ["auto", "always", "off"].indexOf(s.safe_mode)
                                onPicked: function (i) { backend.setSetting("safe_mode", ["auto", "always", "off"][i]) } }
                    Row { spacing: 8
                        Rectangle { width: 9; height: 9; radius: 5; anchors.verticalCenter: parent.verticalCenter
                                    color: safeCard.safe.active ? Tokens.accent : Tokens.dim }
                        Text { color: safeCard.safe.active ? Tokens.text : Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: safeCard.safe.active
                               text: safeCard.safe.active
                                     ? Tr.line(Tr.t("Active now") + (safeCard.safe.game ? "  ·  " + safeCard.safe.game : ""))
                                     : Tr.t("Not active now") }
                    }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.t("Lmonitor never touches a game: it injects nothing and reads no game memory. But games with kernel anti-cheat (Warzone, Valorant, Fortnite...) can object to hardware-sensor drivers. While such a game runs, safe mode stops using the sensor driver, so CPU temperature, power and clock show -- until you close the game. FPS, GPU, RAM and the overlays keep working.") }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.t("No tool can promise what an anti-cheat will accept. Use at your own risk.") }
                }
            }
            Pill { danger: true; label: Tr.t("Reset overlay settings"); onClicked: backend.resetSettings() }
        }
    }
}
