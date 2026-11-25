import QtQuick
import Lmonitor
import "../components"

// Games are noticed automatically (a program drawing frames in front, seen by
// PresentMon); sessions of a minute or longer are saved on this PC.
// Right side: the report of the chosen session - the main numbers, what was noticed in
// plain words, and (on request) every detail; or two sessions compared.
Item {
    id: page
    readonly property var d: tools.sessions
    readonly property var items: d.items || []
    readonly property int g: Tokens.gap
    property int sel: -1
    property var rep: ({})
    property bool details: false
    property bool comparing: false         // picking the second session in the list
    property int other: -1
    property var cmp: ({})
    property string saved: ""
    property bool renaming: false
    // the name belongs to the program: every session of it, now and later, shows it
    function saveName() { tools.programRename(page.rep.exe || "", nameEdit.text); page.renaming = false }

    onItemsChanged: {
        var ok = false, ok2 = false
        for (var i = 0; i < items.length; ++i) { if (items[i].id === sel) ok = true; if (items[i].id === other) ok2 = true }
        if (!ok) { sel = items.length ? items[0].id : -1 }
        if (!ok2) other = -1
        if (Object.keys(open).length === 0 && groups.length) {   // the newest game starts opened
            var o = {}; o[keyOf(groups[0])] = true; open = o
        }
        reload()
    }
    onSelChanged: { details = false; saved = ""; renaming = false; reload() }
    onOtherChanged: reload()
    function reload() {
        rep = sel >= 0 ? tools.sessionReport(sel) : ({})
        cmp = (comparing && other >= 0 && other !== sel) ? tools.sessionCompare(sel, other) : ({})
    }
    function pick(id) {
        if (comparing && id !== sel) other = id
        else if (!comparing) sel = id
    }
    function savePicture() {
        page.saved = ""                      // the box above the report goes away for the picture
        flick.contentY = 0
        Qt.callLater(function () {
            var a = report.mapToItem(null, 0, 0), b = report.mapToItem(null, report.width, report.height)
            var path = tools.sessionImagePath(page.rep.game || "session")
            // then it says at the top where the picture is
            page.saved = tools.saveWindowArea(a.x, a.y, b.x, b.y, path) ? path : "!"
            flick.contentY = 0
        })
    }

    PageHeader {
        id: head; width: parent.width
        kicker: page.d.status || ""; title: Tr.t("Sessions")
        // one minute of the game in front, recorded the same way every time: easy to compare
        Pill { anchors.verticalCenter: parent.verticalCenter
               label: page.d.bench ? Tr.t("Cancel benchmark") : Tr.t("Run a benchmark")
               primary: !page.d.bench; danger: !!page.d.bench
               onClicked: page.d.bench ? tools.benchStop() : tools.benchStart() }
        Text { text: Tr.t("Record games"); color: Tokens.sub; anchors.verticalCenter: parent.verticalCenter
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: page.d.enabled === true
                       onToggled: function (v) { tools.sessionsOn(v) } }
    }

    Column {                                                 // nothing recorded yet
        visible: page.items.length === 0; anchors.centerIn: parent; width: 460; spacing: 16
        Text { width: parent.width; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
               color: page.d.enabled === true ? Tokens.dim : Tokens.warn; font.family: Tokens.font; font.pixelSize: 14
               text: page.d.enabled === true
                     ? Tr.t("No sessions yet. Play a game while Lmonitor is running - sessions of one minute or longer are saved here with FPS, 1% lows, temperatures and what slowed the game down.")
                     : Tr.t("Recording is off, so no game reports are made. Turn it on and play a game for a minute or longer - its report then appears here.") }
        Pill { visible: page.d.enabled !== true; anchors.horizontalCenter: parent.horizontalCenter; primary: true
               label: Tr.t("Turn on recording"); onClicked: tools.sessionsOn(true) }
    }

    // ---- the list: one row per game (never two games in one row); the arrow opens its sessions
    readonly property var groups: d.groups || []
    property var open: ({})                 // game file (lower case) -> true while opened
    property bool selecting: false          // "Select" mode: pick games / sessions to delete
    property var picked: ({})               // "g:<file>" / "s:<id>" -> true
    function keyOf(g) { return (g.exe || "").toLowerCase() }
    function flat() {
        var out = []
        for (var i = 0; i < groups.length; ++i) {
            var gr = groups[i]
            out.push({kind: "g", g: gr})
            if (open[keyOf(gr)])
                for (var k = 0; k < gr.sessions.length; ++k) out.push({kind: "s", s: gr.sessions[k], g: gr})
        }
        return out
    }
    function toggleOpen(gr) { var o = Object.assign({}, open); o[keyOf(gr)] = !o[keyOf(gr)]; open = o }
    function togglePick(key) { var o = Object.assign({}, picked); if (o[key]) delete o[key]; else o[key] = true; picked = o }
    function pickedIds() {
        var ids = {}
        for (var i = 0; i < groups.length; ++i) {
            var gr = groups[i], whole = !!picked["g:" + keyOf(gr)]
            for (var k = 0; k < gr.sessions.length; ++k)
                if (whole || picked["s:" + gr.sessions[k].id]) ids[gr.sessions[k].id] = true
        }
        return Object.keys(ids).map(function (x) { return parseInt(x) })
    }
    function endSelect() { selecting = false; picked = ({}) }

    Card {                                                   // list
        id: listCard
        visible: page.items.length > 0
        y: head.height + 12; width: 340; height: parent.height - y
        Item {                                               // list header
            id: listHead; x: 16; y: 10; width: parent.width - 32; height: 34
            Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width - selBtn.width - 8; elide: Text.ElideRight
                   text: page.comparing ? Tr.t("Pick the session to compare with.")
                         : page.selecting ? Tr.t("Pick what to delete") : Tr.t("Games")
                   color: page.comparing ? Tokens.info : Tokens.text
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            Pill { id: selBtn; visible: !page.comparing; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                   height: 30; label: page.selecting ? Tr.t("Cancel") : Tr.t("Select")
                   onClicked: page.selecting ? page.endSelect() : (page.selecting = true) }
        }
        ListView {
            id: lv
            x: 10; y: listHead.y + listHead.height + 6; width: parent.width - 20
            height: parent.height - y - (delBar.visible ? delBar.height + 12 : 10)
            clip: true; spacing: 4
            model: page.flat(); boundsBehavior: Flickable.StopAtBounds
            delegate: Rectangle {
                id: row
                readonly property bool isG: modelData.kind === "g"
                readonly property var gr: modelData.g
                readonly property var se: modelData.s || ({})
                readonly property string pk: isG ? "g:" + page.keyOf(gr) : "s:" + se.id
                readonly property bool isPicked: !!page.picked[pk] || (!isG && !!page.picked["g:" + page.keyOf(gr)])
                readonly property bool isSel: !isG && se.id === page.sel
                readonly property bool isOther: !isG && page.comparing && se.id === page.other
                readonly property bool opened: isG && !!page.open[page.keyOf(gr)]
                width: lv.width; height: isG ? 62 : 52; radius: 10
                color: isPicked ? Tokens.tint(Tokens.danger, 0.14) : isSel ? Tokens.accentA(0.16)
                       : isOther ? Tokens.tint(Tokens.info, 0.16) : (rma.containsMouse ? Tokens.fg(0.05) : "transparent")
                border.width: isSel || isOther || isPicked ? 1 : 0
                border.color: isPicked ? Tokens.danger : isOther ? Tokens.info : Tokens.accent
                Rectangle {                                  // check box in Select mode
                    id: box
                    visible: page.selecting
                    x: row.isG ? 10 : 30; anchors.verticalCenter: parent.verticalCenter
                    width: 18; height: 18; radius: 5; color: row.isPicked ? Tokens.danger : "transparent"
                    border.width: 2; border.color: row.isPicked ? Tokens.danger : Tokens.lineStrong
                    Text { anchors.centerIn: parent; visible: row.isPicked; text: "\uE73E"; color: "white"
                           font.family: Tokens.iconFont; font.pixelSize: 11 }
                }
                // a game: arrow, name, how many sessions, total time, how it plays compared with its usual
                Item {
                    visible: row.isG
                    x: page.selecting ? 36 : 6; width: parent.width - x - 10; height: parent.height
                    Text { id: arrow; anchors.verticalCenter: parent.verticalCenter; width: 24; horizontalAlignment: Text.AlignHCenter
                           text: "\uE70D"; color: amA.containsMouse ? Tokens.accent : Tokens.sub
                           font.family: Tokens.iconFont; font.pixelSize: 12; rotation: row.opened ? 0 : -90
                           Behavior on rotation { NumberAnimation { duration: 120 } }
                           MouseArea { id: amA; anchors.fill: parent; anchors.margins: -8; hoverEnabled: true
                                       cursorShape: Qt.PointingHandCursor; onClicked: page.toggleOpen(row.gr) } }
                    Column {
                        x: 30; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 30 - chip.width - 6; spacing: 3
                        Text { width: parent.width; elide: Text.ElideRight; color: Tokens.text
                               text: (row.gr.name || "") + (row.gr.live ? Tr.t("  ● recording") : "")
                               font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                        Text { width: parent.width; elide: Text.ElideRight; color: Tokens.dim
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                               text: Tr.line(row.gr.count + Tr.t(row.gr.count === 1 ? " session" : " sessions") + "  ·  " + row.gr.total) }
                    }
                    Rectangle {
                        id: chip
                        visible: !!row.gr.status
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        width: visible ? chipT.implicitWidth + 14 : 0; height: 22; radius: 6
                        color: row.gr.status === "slower than usual" ? Tokens.tint(Tokens.warn, 0.15)
                               : row.gr.status === "faster than usual" ? Tokens.accentA(0.15) : Tokens.fg(0.06)
                        Text { id: chipT; anchors.centerIn: parent; text: Tr.t(row.gr.status || "")
                               color: row.gr.status === "slower than usual" ? Tokens.warn
                                      : row.gr.status === "faster than usual" ? Tokens.accent : Tokens.sub
                               font.family: Tokens.font; font.pixelSize: 11; font.weight: Font.DemiBold }
                    }
                }
                // one launch of the game
                Column {
                    visible: !row.isG
                    x: page.selecting ? 56 : 34; anchors.verticalCenter: parent.verticalCenter; width: parent.width - x - 10; spacing: 2
                    Text { width: parent.width; elide: Text.ElideRight; color: Tokens.text
                           text: Tr.line((row.se.bench ? Tr.t("Benchmark") + "  ·  " : "") + (row.se.when || "") + "  ·  " + (row.se.duration || ""))
                           font.family: Tokens.font; font.pixelSize: 13; font.weight: Font.DemiBold }
                    Text { color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.line((row.se.avg_fps !== null && row.se.avg_fps !== undefined ? Math.round(row.se.avg_fps) + Tr.t(" FPS avg") : Tr.t("FPS n/a"))
                                 + (row.se.low1 !== null && row.se.low1 !== undefined ? Tr.t("  ·  1% low ") + Math.round(row.se.low1) : "")
                                 + (row.se.live ? Tr.t("  ● recording") : "")) }
                }
                MouseArea {
                    id: rma; anchors.fill: parent; z: -1; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        if (page.selecting) { page.togglePick(row.pk); return }
                        if (row.isG) {
                            if (!row.opened) page.toggleOpen(row.gr)
                            if (row.gr.sessions.length) page.pick(row.gr.sessions[0].id)   // its newest session
                        } else page.pick(row.se.id)
                    }
                }
            }
        }
        Item {                                               // delete what was picked
            id: delBar
            visible: page.selecting
            x: 12; width: parent.width - 24; height: 40; anchors.bottom: parent.bottom; anchors.bottomMargin: 10
            readonly property int n: page.pickedIds().length
            Text { anchors.verticalCenter: parent.verticalCenter; color: Tokens.sub; font.family: Tokens.font
                   font.pixelSize: Tokens.fsSmall; text: Tr.line(delBar.n + Tr.t(" session(s) picked")) }
            ConfirmButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; danger: true
                            ready: delBar.n > 0; label: Tr.t("Delete")
                            question: Tr.line(Tr.t("Delete ") + delBar.n + Tr.t(" session(s)?"))
                            onConfirmed: { tools.sessionsDelete(page.pickedIds()); page.endSelect() } }
        }
    }

    Flickable {                                              // the report
        id: flick
        visible: page.items.length > 0 && page.sel >= 0
        x: listCard.width + page.g; y: head.height + 12; width: parent.width - x; height: parent.height - y
        contentWidth: width; contentHeight: dcol.height + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds
        Column {
            id: dcol; width: parent.width - 8; spacing: page.g

            Rectangle {                                      // where the picture went
                id: savedBox
                visible: page.saved !== ""; width: dcol.width; height: visible ? savedCol.height + 24 : 0; radius: 10
                color: page.saved === "!" ? Tokens.tint(Tokens.danger, 0.12) : Tokens.accentA(0.10)
                border.width: 1; border.color: page.saved === "!" ? Tokens.danger : Tokens.accent
                Column {
                    id: savedCol; x: 14; y: 12; width: parent.width - 28 - (openPic.visible ? openPic.width + 12 : 0); spacing: 4
                    Text { text: page.saved === "!" ? Tr.t("The picture could not be saved.") : Tr.t("Picture saved here:")
                           color: page.saved === "!" ? Tokens.danger : Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    TextEdit { visible: page.saved !== "!"; width: parent.width; wrapMode: TextEdit.WrapAnywhere
                               readOnly: true; selectByMouse: true; text: page.saved; color: Tokens.text
                               id: savedPath
                               transform: Scale { origin.x: savedPath.width / 2; xScale: Tr.rtl ? -1 : 1 }
                               horizontalAlignment: Tr.rtl ? TextEdit.AlignRight : TextEdit.AlignLeft
                               selectionColor: Tokens.accentA(0.4); font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                }
                Pill { id: openPic; visible: page.saved !== "!"; anchors.right: parent.right; anchors.rightMargin: 12
                       anchors.verticalCenter: parent.verticalCenter; label: Tr.t("Show in folder")
                       onClicked: tools.showFile(page.saved) }
            }
            Card {                                           // ---- main numbers + what was noticed
                id: report
                width: dcol.width; height: rcol.height + 36
                Column {
                    id: rcol; x: 20; y: 18; width: parent.width - 40; spacing: 14
                    Column { width: parent.width; spacing: 2
                        Item {                               // the name - click the pencil to give it your own
                            width: parent.width; height: 30
                            Row {
                                visible: !page.renaming; spacing: 8; anchors.verticalCenter: parent.verticalCenter
                                Text { id: nameText; text: page.rep.game || ""; color: Tokens.text; elide: Text.ElideRight
                                       width: Math.min(implicitWidth, rcol.width - 40)
                                       font.family: Tokens.fontDisplay; font.pixelSize: 20; font.weight: Font.DemiBold }
                                Text { text: "\uE70F"; color: penMa.containsMouse ? Tokens.accent : Tokens.sub
                                       anchors.verticalCenter: parent.verticalCenter
                                       font.family: Tokens.iconFont; font.pixelSize: 15
                                       MouseArea { id: penMa; anchors.fill: parent; anchors.margins: -6; hoverEnabled: true
                                                   cursorShape: Qt.PointingHandCursor
                                                   onClicked: { page.renaming = true; nameEdit.text = page.rep.game || ""
                                                                nameEdit.selectAll(); nameEdit.forceActiveFocus() } } }
                            }
                            Rectangle {
                                visible: page.renaming; width: parent.width; height: 34; radius: 8
                                color: Tokens.bg0; border.width: 1; border.color: Tokens.accent
                                TextInput {
                                    id: nameEdit
                                    x: 10; width: parent.width - 20 - doneRow.width; anchors.verticalCenter: parent.verticalCenter
                                    color: Tokens.text; selectionColor: Tokens.accentA(0.4); maximumLength: 60; clip: true
                                    font.family: Tokens.fontDisplay; font.pixelSize: 17
                                    transform: Scale { origin.x: nameEdit.width / 2; xScale: Tr.rtl ? -1 : 1 }
                                    horizontalAlignment: Tr.rtl ? TextInput.AlignRight : TextInput.AlignLeft
                                    onAccepted: page.saveName()
                                    Keys.onEscapePressed: page.renaming = false
                                }
                                Row { id: doneRow; anchors.right: parent.right; anchors.rightMargin: 4; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                                    Pill { height: 26; label: Tr.t("Save"); primary: true; onClicked: page.saveName() }
                                    Pill { height: 26; label: Tr.t("Cancel"); onClicked: page.renaming = false } }
                            }
                        }
                        Text { visible: page.renaming; width: parent.width; wrapMode: Text.WordWrap
                               text: Tr.t("This name is used for every session of this game, now and later. Leave it empty for the game's own name.")
                               color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                        Text { text: Tr.line((page.rep.title ? page.rep.game_name + "  ·  " : "") + (page.rep.when || "")
                                             + (page.rep.live ? Tr.t("  ·  still recording") : ""))
                               color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall } }
                    Text { width: parent.width; wrapMode: Text.WordWrap; text: Tr.t(page.rep.verdict || "")
                           color: (page.rep.noticed || []).some(function (n) { return n.sev === "warn" }) ? Tokens.warn : Tokens.accent
                           font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                    Grid {                                   // 4 x 2 numbers
                        id: tiles; width: parent.width; columns: 4; columnSpacing: 10; rowSpacing: 10
                        readonly property real tw: (width - 3 * columnSpacing) / 4
                        Repeater {
                            model: page.rep.tiles || []
                            Rectangle {
                                width: tiles.tw; height: 70; radius: 10; color: Tokens.bg0
                                border.width: 1; border.color: Tokens.line
                                Text { x: 12; y: 10; width: parent.width - 24; elide: Text.ElideRight; text: Tr.t(modelData.label)
                                       color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                                Row { x: 12; y: 32; spacing: 4
                                    Text { text: modelData.text === null || modelData.text === undefined ? Tr.t("Not measured") : modelData.text
                                           color: modelData.text === null || modelData.text === undefined ? Tokens.dim : Tokens.text
                                           font.family: Tokens.fontDisplay; font.weight: Font.DemiBold
                                           font.pixelSize: modelData.text === null || modelData.text === undefined ? 13 : 22 }
                                    Text { visible: modelData.text !== null && modelData.text !== undefined && modelData.unit !== "" && modelData.unit !== "time"
                                           anchors.baseline: parent.children[0].baseline; text: modelData.unit; color: Tokens.sub
                                           font.family: Tokens.font; font.pixelSize: 12 } }
                            }
                        }
                    }
                    Column {                                 // the same game over time
                        width: parent.width; spacing: 3
                        visible: (page.rep.trend || []).length > 0
                        Text { text: Tr.t("Compared with your earlier sessions of this game"); color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                        Repeater {
                            model: page.rep.trend || []
                            Text { width: parent.width; wrapMode: Text.WordWrap
                                   text: Tr.line(Tr.t(modelData.label) + ": " + Tr.t(modelData.text))
                                   color: modelData.better === true ? Tokens.accent : modelData.better === false ? Tokens.warn : Tokens.sub
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                        }
                    }
                    Text { visible: !!page.rep.ft && page.rep.ft[0] !== null && page.rep.ft[0] !== undefined
                           width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: !page.rep.ft ? "" : Tr.line(Tr.t("Frame time: ") + page.rep.ft[0] + Tr.t(" ms on average")
                                 + (page.rep.ft[1] !== null ? Tr.t(", the slowest 1% of frames ") + page.rep.ft[1] + " ms" : "")
                                 + (page.rep.ft[2] !== null ? Tr.t(", the slowest 0.1% ") + page.rep.ft[2] + " ms" : "")) }

                    Column {                                 // what was noticed
                        width: parent.width; spacing: 10
                        visible: (page.rep.noticed || []).length > 0
                        Text { text: Tr.t("What we noticed"); color: Tokens.text; font.family: Tokens.font
                               font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                        Repeater {
                            model: page.rep.noticed || []
                            Item {
                                id: nItem
                                property bool open: false
                                width: parent.width; height: nCol.height
                                Rectangle { width: 8; height: 8; radius: 4; y: 6
                                            color: modelData.sev === "warn" ? Tokens.warn : modelData.sev === "notice" ? Tokens.info : Tokens.dim }
                                Column {
                                    id: nCol; x: 18; width: parent.width - 18; spacing: 3
                                    Text { width: parent.width; wrapMode: Text.WordWrap; text: Tr.t(modelData.text); color: Tokens.text
                                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                                    Text { visible: modelData.tip !== ""; width: parent.width; wrapMode: Text.WordWrap
                                           text: Tr.t(modelData.tip); color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                                    Text { visible: modelData.more !== ""; text: nItem.open ? Tr.t("Hide the measurements") : Tr.t("Show the measurements")
                                           color: Tokens.accent; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                                           MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: nItem.open = !nItem.open } }
                                    Text { visible: nItem.open; width: parent.width; wrapMode: Text.WordWrap; text: Tr.t(modelData.more)
                                           color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                                }
                            }
                        }
                    }
                    Column {                                 // what a change would likely do (no promised numbers)
                        width: parent.width; spacing: 6
                        visible: (page.rep.whatif || []).length > 0
                        Text { text: Tr.t("What would likely help"); color: Tokens.text; font.family: Tokens.font
                               font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                        Repeater {
                            model: page.rep.whatif || []
                            Item {
                                width: parent.width; height: wiT.implicitHeight
                                Text { y: 1; text: modelData.sure ? "\uE73E" : "\uE9CE"; color: modelData.sure ? Tokens.accent : Tokens.dim
                                       font.family: Tokens.iconFont; font.pixelSize: 12 }
                                Text { id: wiT; x: 20; width: parent.width - 20; wrapMode: Text.WordWrap; text: Tr.t(modelData.text)
                                       color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                            }
                        }
                        Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                               font.family: Tokens.font; font.pixelSize: 12
                               text: Tr.t("Worked out from what this session measured. These are directions, not promises - Lmonitor never guesses exact FPS.") }
                    }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 12
                           text: Tr.t("Only measured values are shown. \"Not measured\" means the sensor or the frame counter was not available - it is never guessed.") }
                }
            }

            Flow {                                           // ---- actions
                width: dcol.width; spacing: 10
                Pill { label: page.comparing ? Tr.t("Stop comparing") : Tr.t("Compare with another session")
                       primary: !page.comparing
                       onClicked: { page.comparing = !page.comparing; page.other = -1; page.reload() } }
                Pill { label: Tr.t("Save as picture"); onClicked: page.savePicture() }
                Pill { label: page.details ? Tr.t("Hide details") : Tr.t("Show all details"); onClicked: page.details = !page.details }
                ConfirmButton { danger: true; label: Tr.t("Delete this session"); question: Tr.t("Delete it?")
                                onConfirmed: tools.sessionDelete(page.sel) }
            }

            Card {                                           // ---- comparison
                visible: page.comparing
                width: dcol.width; height: cCol.height + 36
                Column {
                    id: cCol; x: 20; y: 18; width: parent.width - 40; spacing: 10
                    Text { text: Tr.t("Before and after"); color: Tokens.text; font.family: Tokens.font
                           font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                    Text { visible: page.other < 0; width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                           text: Tr.t("Pick a second session of the same game in the list - for example one from before you changed something (a new driver, cleaned fans, another power plan or other game settings).") }
                    Text { visible: page.other >= 0 && !!page.cmp.note; width: parent.width; wrapMode: Text.WordWrap
                           color: Tokens.warn; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; text: Tr.t(page.cmp.note || "") }
                    Text { visible: page.cmp.ok === true; color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.line(Tr.t("Before: ") + (page.cmp.before || "") + "   ·   " + Tr.t("After: ") + (page.cmp.after || "")) }
                    Repeater {
                        model: page.cmp.ok ? page.cmp.rows : []
                        Item {
                            width: cCol.width; height: 40
                            Rectangle { width: parent.width; height: 1; color: Tokens.line }
                            Text { y: 4; width: parent.width * 0.62; wrapMode: Text.WordWrap; text: Tr.t(modelData.text)
                                   color: modelData.better === true ? Tokens.accent : modelData.better === false ? Tokens.warn : Tokens.text
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: modelData.better !== null }
                            Text { y: 24; text: Tr.t(modelData.label); color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 12 }
                            Text { anchors.right: parent.right; y: 10; text: modelData.before_text + "  →  " + modelData.after_text
                                   color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                        }
                    }
                    Text { visible: (page.cmp.changed || []).length > 0; text: Tr.t("What changed in between"); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    Repeater { model: page.cmp.changed || []
                        Text { width: cCol.width; wrapMode: Text.WordWrap; text: "•  " + Tr.t(modelData); color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall } }
                    Text { visible: page.cmp.ok === true; width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 12
                           text: Tr.t("Small differences (under 3% FPS or 2 °C) count as the same: two plays of a game are never exactly alike.") }
                }
            }

            Repeater {                                       // ---- every detail (on request)
                model: page.details ? (page.rep.details || []) : []
                RowsCard { width: dcol.width; title: modelData.title; rows: modelData.rows }
            }
        }
    }
}
