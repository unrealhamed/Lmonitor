import QtQuick
import Lmonitor
import "../components"

// Real values read from this PC. "n/a" / "--" means the value is not available.
// Sections (CPU, GPU, ...) are cards in two balanced columns.
Item {
    id: page
    property int tab: 0
    readonly property int g: Tokens.gap
    readonly property real colW: (width - g) / 2
    Component.onCompleted: backend.openHardware(page.tab, true)
    Component.onDestruction: backend.openHardware(0, false)

    PageHeader {
        id: head; width: parent.width; kicker: Tr.t("Everything about this PC"); title: Tr.t("Hardware")
        Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Warn me about problems"); color: Tokens.sub
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: backend.alerts.on === true
                       onToggled: function (v) { backend.setAlertsOn(v) } }
    }
    Card {                                       // the latest warnings (they are also shown next to the clock)
        id: warnCard
        readonly property var rec: (backend.alerts.recent || []).slice(0, 3)
        visible: rec.length > 0
        y: head.height + 12; width: parent.width; height: visible ? warnCol.height + 28 : 0
        Column {
            id: warnCol; x: 20; y: 14; width: parent.width - 40; spacing: 8
            Text { text: Tr.t("Recent warnings"); color: Tokens.text; font.family: Tokens.font
                   font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
            Repeater {
                model: warnCard.rec
                Item {
                    width: warnCol.width; height: wt.implicitHeight + wtip.implicitHeight + 4
                    Text { id: wtime; text: modelData.when; color: Tokens.dim; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           width: 44; y: 1 }
                    Text { id: wt; x: 50; width: parent.width - 50; wrapMode: Text.WordWrap; text: Tr.t(modelData.title)
                           color: Tokens.warn; font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    Text { id: wtip; x: 50; y: wt.implicitHeight + 2; width: parent.width - 50; wrapMode: Text.WordWrap
                           text: Tr.t(modelData.tip); color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                }
            }
        }
    }
    Segmented {
        id: tabs; y: head.height + 12 + (warnCard.visible ? warnCard.height + page.g : 0); width: Math.min(parent.width, 760)
        model: backend.hardwareTabs; index: page.tab
        onPicked: function (i) { page.tab = i; backend.openHardware(i, true) }
    }

    Flickable {
        y: tabs.y + tabs.height + page.g
        width: parent.width; height: parent.height - y
        contentWidth: width; contentHeight: Math.max(page.c0 ? page.c0.height : 0, page.c1 ? page.c1.height : 0) + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Repeater {
            model: 2
            Column {
                id: colItem
                x: index * (page.colW + page.g); width: page.colW; spacing: page.g
                Component.onCompleted: { if (index === 0) page.c0 = colItem; else page.c1 = colItem }
                Repeater {
                    model: backend.hardware.length > index ? backend.hardware[index] : []
                    RowsCard { width: parent.width; title: modelData.title; rows: modelData.rows }
                }
            }
        }
    }
    property var c0: null
    property var c1: null
}
