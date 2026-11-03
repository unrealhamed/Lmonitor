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

    PageHeader { id: head; width: parent.width; kicker: "Saved on this PC only"; title: "Reports"
                 Pill { label: page.busy ? "Working…" : "Rebuild"; onClicked: if (!page.busy) tools.repBuild() } }
    ResultBanner { id: banner; y: head.height + 8; width: parent.width
                   result: page.d.last; onDismissed: tools.repDismiss() }

    Row {
        y: head.height + 8 + (banner.visible ? banner.height + page.g : 0)
        width: parent.width; spacing: page.g
        Card {                                               // score
            width: 300; height: 230; tint: true
            Text { x: 22; y: 18; text: "Health score"; color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
            Text { x: 22; y: 44; text: page.d.built && page.d.score !== null && page.d.score !== undefined ? page.d.score : "--"
                   color: Tokens.text; font.family: Tokens.font; font.pixelSize: 64; font.bold: true }
            Text { x: 22; y: 126; width: parent.width - 44; wrapMode: Text.Wrap; color: Tokens.dim
                   text: page.d.built && page.d.score !== null && page.d.score !== undefined
                         ? "out of 100 - " + page.d.covered + " of " + page.d.total + " checks answered"
                         : "Run a scan in Diagnostics first." 
                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        }
        Card {                                               // contents + save
            width: parent.width - 300 - page.g; height: 230
            Text { x: 22; y: 18; text: "What the report contains"; color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
            Column { x: 22; y: 54; spacing: 8
                Repeater {
                    model: [["Last scan", page.d.built ? (page.d.scan_time || "none yet") : ""],
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
                Pill { primary: true; label: "Save HTML report"; onClicked: if (!page.busy) tools.repSave("html") }
                Pill { label: "Save JSON"; onClicked: if (!page.busy) tools.repSave("json") }
                Pill { label: "Open folder"; onClicked: tools.repOpen() }
            }
        }
    }
}
