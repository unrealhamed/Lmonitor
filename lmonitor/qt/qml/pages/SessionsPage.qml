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

    onItemsChanged: {
        var ok = false, ok2 = false
        for (var i = 0; i < items.length; ++i) { if (items[i].id === sel) ok = true; if (items[i].id === other) ok2 = true }
        if (!ok) { sel = items.length ? items[0].id : -1 }
        if (!ok2) other = -1
        reload()
    }
    onSelChanged: { details = false; saved = ""; reload() }
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
        flick.contentY = 0
        Qt.callLater(function () {
            var a = report.mapToItem(null, 0, 0), b = report.mapToItem(null, report.width, report.height)
            var path = tools.sessionImagePath(page.rep.game || "session")
            if (tools.saveWindowArea(a.x, a.y, b.x, b.y, path)) { page.saved = path; tools.showFile(path) }
            else page.saved = "!"
        })
    }

    PageHeader {
        id: head; width: parent.width
        kicker: page.d.status || ""; title: Tr.t("Sessions")
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

    Card {                                                   // list
        id: listCard
        visible: page.items.length > 0
        y: head.height + 12; width: 330; height: parent.height - y
        Text { id: pickHint; visible: page.comparing; x: 16; y: 12; width: parent.width - 32; wrapMode: Text.WordWrap
               text: Tr.t("Pick the session to compare with."); color: Tokens.info
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
        ListView {
            anchors.fill: parent; anchors.margins: 10; anchors.topMargin: page.comparing ? pickHint.height + 20 : 10
            clip: true; spacing: 6
            model: page.items; boundsBehavior: Flickable.StopAtBounds
            delegate: Rectangle {
                readonly property bool isSel: modelData.id === page.sel
                readonly property bool isOther: page.comparing && modelData.id === page.other
                width: ListView.view.width; height: 66; radius: 12
                color: isSel ? Tokens.accentA(0.16) : isOther ? Tokens.tint(Tokens.info, 0.16)
                       : (ma.containsMouse ? Tokens.fg(0.05) : "transparent")
                border.width: isSel || isOther ? 1 : 0; border.color: isOther ? Tokens.info : Tokens.accent
                Column { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; spacing: 2
                    Text { width: parent.width; elide: Text.ElideRight; text: modelData.game + (modelData.live ? Tr.t("  ● recording") : "")
                           color: Tokens.text; font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                    Text { text: modelData.when + "  ·  " + modelData.duration; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10 }
                    Text { color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.line((modelData.avg_fps !== null && modelData.avg_fps !== undefined ? Math.round(modelData.avg_fps) + Tr.t(" FPS avg") : Tr.t("FPS n/a"))
                                 + (modelData.low1 !== null && modelData.low1 !== undefined ? Tr.t("  ·  1% low ") + Math.round(modelData.low1) : "")) } }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: page.pick(modelData.id) }
            }
        }
    }

    Flickable {                                              // the report
        id: flick
        visible: page.items.length > 0 && page.sel >= 0
        x: 330 + page.g; y: head.height + 12; width: parent.width - x; height: parent.height - y
        contentWidth: width; contentHeight: dcol.height + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds
        Column {
            id: dcol; width: parent.width - 8; spacing: page.g

            Card {                                           // ---- main numbers + what was noticed
                id: report
                width: dcol.width; height: rcol.height + 36
                Column {
                    id: rcol; x: 20; y: 18; width: parent.width - 40; spacing: 14
                    Column { width: parent.width; spacing: 2
                        Text { width: parent.width; elide: Text.ElideRight; text: page.rep.game || ""; color: Tokens.text
                               font.family: Tokens.fontDisplay; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { text: Tr.line((page.rep.when || "") + (page.rep.live ? Tr.t("  ·  still recording") : ""))
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
                                            color: modelData.sev === "warn" ? Tokens.warn : Tokens.info }
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
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 11
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
            Text { visible: page.saved !== ""; width: dcol.width; wrapMode: Text.WordWrap
                   color: page.saved === "!" ? Tokens.danger : Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                   text: page.saved === "!" ? Tr.t("The picture could not be saved.") : Tr.line(Tr.t("Saved: ") + page.saved) }

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
                            Text { y: 24; text: Tr.t(modelData.label); color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 11 }
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
                           font.family: Tokens.font; font.pixelSize: 11
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
