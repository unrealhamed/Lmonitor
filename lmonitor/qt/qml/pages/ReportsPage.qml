import QtQuick
import Lmonitor
import "../components"

// A shareable summary of the last scan, your game sessions and the changes
// made. Nothing is uploaded and Windows user names are hidden.
Item {
    id: page
    readonly property var d: tools.reports
    readonly property bool busy: d.busy === true
    readonly property int g: Tokens.gap

    PageHeader { id: head; width: parent.width; kicker: Tr.t("Saved on this PC only"); title: Tr.t("PC check")
                 Pill { primary: true; label: page.busy ? Tr.t("Working…") : Tr.t("Scan PC"); onClicked: if (!page.busy) tools.repScan() }
                 Pill { label: page.busy ? Tr.t("Working…") : Tr.t("Rebuild"); onClicked: if (!page.busy) tools.repBuild() } }
    ResultBanner { id: banner; y: head.height + 8; width: parent.width
                   result: page.d.last; onDismissed: tools.repDismiss() }

    Row {
        id: top
        y: head.height + 8 + (banner.visible ? banner.height + page.g : 0)
        width: parent.width; spacing: page.g
        Card {                                               // score
            width: 300; height: 250; tint: true
            Text { x: 22; y: 18; text: Tr.t("Health score"); color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
            Text { x: 22; y: 44; text: page.d.built && page.d.score !== null && page.d.score !== undefined ? page.d.score : "--"
                   color: Tokens.text; font.family: Tokens.font; font.pixelSize: 64; font.bold: true }
            Text { x: 22; y: 126; width: parent.width - 44; wrapMode: Text.Wrap; color: Tokens.dim
                   text: page.d.built && page.d.score !== null && page.d.score !== undefined
                         ? Tr.line(Tr.t("out of 100 - ") + page.d.covered + Tr.t(" of ") + page.d.total + Tr.t(" checks answered"))
                         : Tr.t("Press Scan PC. The scan only reads - it changes nothing.") 
                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        }
        Card {                                               // contents + save
            width: parent.width - 300 - page.g; height: 250
            Text { x: 22; y: 18; text: Tr.t("What the report contains"); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
            Column { x: 22; y: 54; spacing: 8
                Repeater {
                    model: [["Last scan", page.d.built ? (page.d.scan_time || Tr.t("none yet")) : ""],
                            ["Issues to look at", page.d.built ? page.d.issues : ""],
                            ["Checks that are fine", page.d.built ? page.d.ok_count : ""],
                            ["Game sessions", page.d.built ? page.d.sessions : ""],
                            ["Changes made by Lmonitor", page.d.built ? page.d.changes : ""]]
                    Row { spacing: 12
                        Text { width: 190; text: modelData[0]; color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                        Text { text: modelData[1]; color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true } }
                }
            }
            Row { x: 22; y: parent.height - 58; spacing: 10
                Pill { primary: true; label: Tr.t("Save HTML report"); onClicked: if (!page.busy) tools.repSave("html") }
                Pill { label: Tr.t("Save JSON"); onClicked: if (!page.busy) tools.repSave("json") }
                Pill { label: Tr.t("Open folder"); onClicked: tools.repOpen() }
            }
        }
    }

    // what the scan found, worst first (this list was the old Diagnostics page)
    Card {
        y: top.y + top.height + page.g; width: parent.width; height: parent.height - y
        readonly property var issues: (tools.diag && tools.diag.issues) ? tools.diag.issues : []
        id: found
        Text { x: 22; y: 16; text: Tr.t("What the scan found"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
        Text { anchors.right: parent.right; anchors.rightMargin: 22; y: 20; color: Tokens.dim
               text: tools.diag && tools.diag.running ? Tr.t(tools.diag.progress || "Working…") : ""
               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        Text { visible: found.issues.length === 0; anchors.centerIn: parent; color: Tokens.dim
               text: Tr.t("Nothing to show yet."); font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Flickable {
            x: 22; y: 50; width: parent.width - 44; height: parent.height - 62
            contentWidth: width; contentHeight: list.height; clip: true; boundsBehavior: Flickable.StopAtBounds
            Column {
                id: list; width: parent.width; spacing: 12
                Repeater {
                    model: found.issues
                    Column {
                        width: list.width; spacing: 3
                        Rectangle { visible: index > 0; width: parent.width; height: 1; color: Tokens.line }
                        Item { width: 1; height: index > 0 ? 6 : 0 }
                        Row { spacing: 8
                            Rectangle { width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                        color: Tokens.sevColor(modelData.sev) }
                            Text { text: Tr.t(modelData.title); color: Tokens.text
                                   font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                            Text { text: Tr.t(modelData.area) + "  ·  " + Tr.t(modelData.word); color: Tokens.sevColor(modelData.sev)
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Repeater { model: modelData.evidence
                            Text { width: list.width; wrapMode: Text.Wrap; text: "•  " + Tr.t(modelData); color: Tokens.sub
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall } }
                        Text { width: parent.width; wrapMode: Text.Wrap; text: Tr.t(modelData.explain); color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                        Text { visible: modelData.sev !== "ok"; width: parent.width; wrapMode: Text.Wrap
                               text: Tr.t(modelData.fix); color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                        Pill { visible: modelData.open_text !== ""; label: Tr.t(modelData.open_text)
                               onClicked: tools.diagOpen(modelData.open) }
                    }
                }
            }
        }
    }
}
