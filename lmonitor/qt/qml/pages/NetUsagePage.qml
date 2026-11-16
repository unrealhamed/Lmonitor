import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

// Network usage (opened from the Network card on Home): how much was downloaded / uploaded
// in the last 1 / 15 / 30 days, per day, per hour and per program. The numbers are Windows'
// own records (written about once an hour); Lmonitor reads them only while this page is open.
Item {
    id: page
    readonly property var d: backend.netUsage
    readonly property bool ready: d.state === "ready"
    readonly property var ranges: [1, 15, 30]
    readonly property color cDown: Tokens.cyan
    readonly property color cUp: Tokens.violet
    readonly property int g: Tokens.gap
    Component.onCompleted: backend.setNetUsageOpen(true)
    Component.onDestruction: backend.setNetUsageOpen(false)

    PageHeader {
        id: head
        width: parent.width
        kicker: Tr.t("From Windows' own records")
        title: Tr.t("Network usage")
        Segmented { width: 300; model: ["1 day", "15 days", "30 days"]
                    index: Math.max(0, page.ranges.indexOf(page.d.days || 1))
                    onPicked: function (i) { backend.netUsageRange(page.ranges[i]) } }
        Pill { label: page.d.busy ? Tr.t("Reading...") : Tr.t("Refresh"); onClicked: backend.netUsageRefresh() }
        Pill { label: Tr.t("Back"); onClicked: Window.window.goTo("Home") }
    }

    // ---- not ready: reading / needs admin / error
    Card {
        visible: !page.ready
        x: 0; y: head.height + 12; width: page.width; height: 180
        Column {
            anchors.centerIn: parent; width: parent.width - 80; spacing: 10
            Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                   color: page.d.state === "error" || page.d.state === "admin" ? Tokens.warn : Tokens.text
                   font.family: Tokens.font; font.pixelSize: 18; font.bold: true
                   text: page.d.state === "admin" ? Tr.t("Needs administrator rights")
                         : page.d.state === "error" ? Tr.t("Windows' records could not be read")
                         : Tr.t("Reading Windows' records...") }
            Text { width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                   color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                   text: page.d.state === "admin" ? Tr.t("Windows keeps these records where only administrators can read them. Start Lmonitor normally (it asks for administrator rights).")
                         : page.d.state === "error" ? (page.d.error || "")
                         : Tr.t("This takes a few seconds. Windows writes these records about once an hour, for the last 30 to 60 days.") }
        }
    }

    // ---- totals of the chosen time span
    readonly property real y1: head.height + 12
    Row {
        id: totals
        visible: page.ready
        y: page.y1; width: page.width; spacing: page.g
        Repeater {
            model: 3
            Card {
                id: tot
                readonly property var info: [[Tr.t("Used"), page.d.total, Tokens.text],
                                             [Tr.t("Download"), page.d.down, page.cDown],
                                             [Tr.t("Upload"), page.d.up, page.cUp]][index]
                width: (page.width - 3 * page.g) / 4; height: 78
                Text { x: 18; y: 12; text: tot.info[0]; color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                Text { x: 18; y: 32; text: tot.info[1] || "--"; color: tot.info[2]
                       font.family: Tokens.font; font.pixelSize: 26; font.bold: true }
            }
        }
        Item {
            width: (page.width - 3 * page.g) / 4; height: 78
            Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width; wrapMode: Text.WordWrap
                   color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                   text: Tr.line(Tr.t("Newest record from Windows: ") + (page.d.updated || "--"))
                         + "\n" + Tr.t("After that: measured by Lmonitor (totals only).")
                         + "\n" + Tr.t("Only real adapters (Wi-Fi, Ethernet) are counted.") }
        }
    }

    // ---- days (15 / 30 days): click one to see it below
    readonly property bool manyDays: page.ready && (page.d.days || 1) > 1
    Card {
        id: daysCard
        visible: page.manyDays
        x: 0; y: totals.y + 78 + page.g; width: page.width; height: page.manyDays ? 196 : 0
        Text { x: 18; y: 12; text: Tr.t("Per day - click a day"); color: Tokens.text
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.bold: true }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 18; y: 14; spacing: 14
            Repeater {
                model: 2
                Row { spacing: 6
                      Rectangle { width: 10; height: 10; radius: 5; y: 3; color: index === 0 ? page.cDown : page.cUp }
                      Text { text: index === 0 ? Tr.t("Download") : Tr.t("Upload"); color: Tokens.sub
                             font.family: Tokens.font; font.pixelSize: Tokens.fsSmall } }
            }
        }
        Item {
            id: dayPlot
            x: 18; y: 40; width: parent.width - 36; height: parent.height - 40 - 26
            readonly property var bars: page.d.bars || []
            readonly property real slot: bars.length ? width / bars.length : width
            Repeater {
                model: dayPlot.bars.length
                Item {
                    readonly property var b: dayPlot.bars[index] || ({})
                    x: index * dayPlot.slot; width: dayPlot.slot; height: dayPlot.height
                    Rectangle { anchors.fill: parent; anchors.margins: 1; radius: 4
                                color: parent.b.sel ? Tokens.accentA(0.16) : dayMouse.containsMouse ? Tokens.fg(0.06) : "transparent"
                                border.width: parent.b.sel ? 1 : 0; border.color: Tokens.accent }
                    Rectangle {                       // download (bottom) + upload (on top)
                        id: downBar
                        x: parent.width * 0.2; width: parent.width * 0.6; radius: 2
                        height: Math.max(parent.b.down > 0 ? 2 : 0, (parent.height - 18) * (parent.b.down || 0))
                        y: parent.height - height; color: page.cDown
                    }
                    Rectangle {
                        x: downBar.x; width: downBar.width; radius: 2
                        height: Math.max(parent.b.up > 0 ? 2 : 0, (parent.height - 18) * (parent.b.up || 0))
                        y: downBar.y - height; color: page.cUp
                    }
                    Text { anchors.horizontalCenter: parent.horizontalCenter; y: parent.height + 4
                           text: dayPlot.bars.length > 15 ? String(parent.b.day || "") : (parent.b.label || "")
                           color: parent.b.sel ? Tokens.text : Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10; font.bold: parent.b.sel === true }
                    MouseArea { id: dayMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: backend.netUsageDay(parent.b.start) }
                    Rectangle {                       // hover: the day and its total
                        visible: dayMouse.containsMouse; z: 5
                        width: tip.implicitWidth + 16; height: 24; radius: 6; color: Tokens.cardHi
                        border.width: 1; border.color: Tokens.line
                        x: Math.max(-parent.x, Math.min(dayPlot.width - parent.x - width, (parent.width - width) / 2)); y: -26
                        Text { id: tip; anchors.centerIn: parent; text: Tr.line((parent.parent.b.label || "") + "  " + (parent.parent.b.text || ""))
                               color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    }
                }
            }
        }
    }

    // ---- the chosen day: per hour (click an hour) and per program
    Card {
        visible: page.ready
        x: 0; y: page.manyDays ? daysCard.y + daysCard.height + page.g : totals.y + 78 + page.g
        width: page.width; height: page.height - y
        Text { x: 18; y: 12; width: parent.width * 0.56; elide: Text.ElideRight
               text: page.d.dayText || ""; color: Tokens.text
               font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.bold: true }
        Text { x: 18; y: 34; text: Tr.line(Tr.t("Used: ") + (page.d.dayTotal || "--") + "   ↓ " + (page.d.dayDown || "--")
                                          + "   ↑ " + (page.d.dayUp || "--"))
               color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        Text { x: 18; y: 54; text: Tr.t("Per hour - click an hour to see its programs"); color: Tokens.dim
               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
        Item {
            id: hourPlot
            x: 18; y: 84; width: parent.width * 0.56 - 18; height: parent.height - 84 - 34
            readonly property var hrs: page.d.hours || []
            readonly property real slot: width / 24
            Repeater { model: 3
                       Rectangle { width: hourPlot.width; height: 1; color: Tokens.line
                                   y: Math.round(index * (hourPlot.height - 1) / 2) } }
            Repeater {
                model: 24
                Item {
                    readonly property var h: hourPlot.hrs[index] || ({})
                    readonly property bool sel: page.d.hour === index
                    x: index * hourPlot.slot; width: hourPlot.slot; height: hourPlot.height
                    Rectangle { anchors.fill: parent; anchors.margins: 1; radius: 3
                                color: parent.sel ? Tokens.accentA(0.16) : hourMouse.containsMouse ? Tokens.fg(0.06) : "transparent"
                                border.width: parent.sel ? 1 : 0; border.color: Tokens.accent }
                    Rectangle { id: hDown; x: parent.width * 0.18; width: parent.width * 0.64; radius: 2
                                height: Math.max(parent.h.down > 0 ? 2 : 0, (parent.height - 6) * (parent.h.down || 0))
                                y: parent.height - height; color: page.cDown }
                    Rectangle { x: hDown.x; width: hDown.width; radius: 2
                                height: Math.max(parent.h.up > 0 ? 2 : 0, (parent.height - 6) * (parent.h.up || 0))
                                y: hDown.y - height; color: page.cUp }
                    Text { visible: index % 3 === 0; anchors.horizontalCenter: parent.horizontalCenter; y: parent.height + 4
                           text: String(index); color: parent.sel ? Tokens.text : Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10 }
                    MouseArea { id: hourMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: backend.netUsageHour(index) }
                    Rectangle {
                        visible: hourMouse.containsMouse; z: 5
                        width: htip.implicitWidth + 16; height: 24; radius: 6; color: Tokens.cardHi
                        border.width: 1; border.color: Tokens.line
                        x: Math.max(-parent.x, Math.min(hourPlot.width - parent.x - width, (parent.width - width) / 2)); y: -26
                        Text { id: htip; anchors.centerIn: parent; color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                               text: Tr.line(("0" + index).slice(-2) + ":00-" + ("0" + ((index + 1) % 24)).slice(-2) + ":00  "
                                             + (parent.parent.h.empty ? Tr.t("nothing") : (parent.parent.h.text || ""))) }
                    }
                }
            }
        }
        // programs of the day (or of the chosen hour)
        Item {
            x: parent.width * 0.56 + 12; y: 12; width: parent.width * 0.44 - 30; height: parent.height - 24
            Text { id: appsTitle; width: parent.width; elide: Text.ElideRight; color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.bold: true
                   text: page.d.hour >= 0
                         ? Tr.line(Tr.t("Programs at ") + ("0" + page.d.hour).slice(-2) + ":00-" + ("0" + ((page.d.hour + 1) % 24)).slice(-2) + ":00")
                         : Tr.t("Programs - whole day") }
            Text { id: appsNote; y: 22; width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                   text: Tr.t("\"System (Windows)\" is Windows itself, and traffic Windows carries for a VPN.") }
            Text { visible: (page.d.apps || []).length === 0; y: appsNote.y + appsNote.height + 20; width: parent.width
                   horizontalAlignment: Text.AlignHCenter; color: Tokens.dim
                   text: Tr.t("Nothing was used in this time"); font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
            ListView {
                y: appsNote.y + appsNote.height + 8; width: parent.width; height: parent.height - y
                clip: true; spacing: 6; boundsBehavior: Flickable.StopAtBounds
                model: page.d.apps || []
                delegate: Item {
                    width: ListView.view.width; height: 40
                    Text { width: parent.width - 120; elide: Text.ElideRight; text: Tr.t(modelData.name)
                           color: modelData.name === page.d.live ? Tokens.accent : Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    Text { anchors.right: parent.right; text: modelData.total; color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    Rectangle { y: 20; width: parent.width; height: 5; radius: 3; color: Tokens.track
                                Rectangle { width: Math.max(3, parent.width * modelData.frac); height: parent.height; radius: 3
                                            color: Tokens.accent } }
                    Text { y: 27; text: Tr.line("↓ " + modelData.down + "   ↑ " + modelData.up); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10 }
                }
            }
        }
    }
}
