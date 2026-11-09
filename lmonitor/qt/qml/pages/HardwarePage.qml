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

    PageHeader { id: head; width: parent.width; kicker: Tr.t("Everything about this PC"); title: Tr.t("Hardware") }
    Segmented {
        id: tabs; y: head.height + 12; width: Math.min(parent.width, 760)
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
