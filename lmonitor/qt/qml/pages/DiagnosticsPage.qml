import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

// Windows checks (startup, power, disks, events, drivers, devices, memory,
// services, settings). "Unknown" means a check could not be done - it is not a
// sign of a problem.
Item {
    id: page
    readonly property var d: tools.diag
    readonly property var sum: d.summary || ({})
    readonly property int g: Tokens.gap

    PageHeader {
        id: head; width: parent.width
        kicker: page.d.has ? Tr.t("Last scan: ") + page.d.when : Tr.t("No scan yet")
        title: Tr.t("Diagnostics")
        Pill { primary: true; label: page.d.running ? Tr.t("Scanning…") : Tr.t("Scan now")
               onClicked: if (!page.d.running) tools.diagScan() }
    }

    Row {                                              // counts
        id: counts
        y: head.height + 12; width: parent.width; spacing: page.g
        Repeater {
            model: [{k: "warn", t: Tr.t("Warnings")}, {k: "notice", t: Tr.t("Notices")}, {k: "unknown", t: Tr.t("Unknown")},
                    {k: "info", t: Tr.t("Info")}, {k: "ok", t: Tr.t("OK")}]
            Card {
                width: (parent.width - 4 * page.g) / 5; height: 78
                Rectangle { x: 18; y: 22; width: 8; height: 8; radius: 4; color: Tokens.sevColor(modelData.k) }
                Text { x: 34; y: 16; text: Tr.t(modelData.t); color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                Text { x: 18; y: 36; text: page.d.has ? (page.sum[modelData.k] || 0) : "--"; color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: 28; font.bold: true }
            }
        }
    }
    Text { id: prog; y: counts.y + counts.height + 8; visible: page.d.running; text: page.d.progress
           color: Tokens.accent; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }

    Text { visible: !page.d.has && !page.d.running; anchors.centerIn: parent; width: 420; wrapMode: Text.Wrap
           horizontalAlignment: Text.AlignHCenter; color: Tokens.dim
           text: Tr.t("Press “Scan now”. The scan only reads Windows settings - it changes nothing.")
           font.family: Tokens.font; font.pixelSize: 14 }

    Flickable {
        y: counts.y + counts.height + 14 + (prog.visible ? 22 : 0)
        width: parent.width; height: parent.height - y
        contentWidth: width; contentHeight: list.height + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds
        Column {
            id: list; width: parent.width - 8; spacing: 10
            Repeater {
                model: page.d.issues || []
                Card {
                    id: it
                    property bool open: false
                    width: list.width; height: 18 + inner.height + 16
                    Column {
                        id: inner; x: 20; y: 14; width: parent.width - 40; spacing: 10
                        Item {
                            width: parent.width; height: 26
                            Rectangle { y: 9; width: 8; height: 8; radius: 4; color: Tokens.sevColor(modelData.sev) }
                            Text { x: 20; anchors.verticalCenter: parent.verticalCenter; text: Tr.t(modelData.title)
                                   color: Tokens.text; font.family: Tokens.font; font.pixelSize: 15; font.bold: true }
                            Text { anchors.right: chev.left; anchors.rightMargin: 14; anchors.verticalCenter: parent.verticalCenter
                                   text: Tr.t(modelData.area) + "  ·  " + Tr.t(modelData.word); color: Tokens.sevColor(modelData.sev)
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
                            Text { id: chev; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                   text: it.open ? "▲" : "▼"; color: Tokens.dim; font.pixelSize: 11 }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: it.open = !it.open }
                        }
                        Column {
                            visible: it.open; width: parent.width; spacing: 8
                            Text { text: Tr.t("WHAT WAS SEEN"); color: Tokens.sub; font.family: Tokens.font; font.pixelSize: 10; font.bold: true }
                            Repeater { model: modelData.evidence
                                Text { width: parent.width; wrapMode: Text.Wrap; text: "•  " + modelData; color: Tokens.text
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody } }
                            Text { text: Tr.t("WHY IT MATTERS"); color: Tokens.sub; font.family: Tokens.font; font.pixelSize: 10; font.bold: true }
                            Text { width: parent.width; wrapMode: Text.Wrap; text: Tr.t(modelData.explain); color: Tokens.text
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                            Text { text: Tr.t("WHAT YOU CAN DO"); color: Tokens.sub; font.family: Tokens.font; font.pixelSize: 10; font.bold: true }
                            Text { width: parent.width; wrapMode: Text.Wrap; text: Tr.t(modelData.fix); color: Tokens.text
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                            Row { spacing: 10; visible: modelData.open_text !== "" || modelData.goto !== ""
                                Pill { visible: modelData.goto !== ""; primary: true; label: Tr.t("Fix in ") + modelData.goto + "  ›"
                                       onClicked: Window.window.goTo(modelData.goto) }
                                Pill { visible: modelData.open_text !== ""; label: modelData.open_text
                                       onClicked: tools.diagOpen(modelData.open) } }
                        }
                    }
                }
            }
        }
    }
}
