import QtQuick
import QtQuick.Window
import Lmonitor
import "components"
import "pages"

Window {
    id: win
    width: 1320; height: 820; minimumWidth: 1120; minimumHeight: 760
    visible: true
    title: "Lmonitor"
    color: Tokens.bg0

    property int page: 0
    Repeater {                              // the chosen app theme drives the shared tokens
        model: ["bg0", "bg1", "card", "cardHi", "line", "text", "sub", "dim", "accent", "light", "accentText"]
        Item { Binding { target: Tokens; property: modelData
                         value: backend.ui[modelData]
                         when: backend.ui[modelData] !== undefined } }
    }
    // header rows have no page; the rest are pages in this order
    readonly property var nav: [
        {head: "MAIN"},
        {label: "Home", src: "pages/Dashboard.qml", live: true},
        {label: "Graphs", src: "pages/GraphsPage.qml", live: true},
        {label: "Hardware", src: "pages/HardwarePage.qml"},
        {head: "GAMING"},
        {label: "Overlay", src: "pages/OverlayPage.qml"},
        {label: "Sessions", src: "pages/SessionsPage.qml", tool: "sessions"},
        {head: "TOOLS"},
        {label: "Diagnostics", src: "pages/DiagnosticsPage.qml", tool: "diag"},
        {label: "Optimizer", src: "pages/OptimizerPage.qml", tool: "opt"},
        {label: "Storage", src: "pages/StoragePage.qml", tool: "storage"},
        {label: "Reports", src: "pages/ReportsPage.qml", tool: "reports"},
        {head: ""},
        {label: "Personalize", src: "pages/PersonalizePage.qml"},
        {label: "About", src: "pages/About.qml"}
    ]
    readonly property var pages: nav.filter(function (n) { return n.label !== undefined })
    function indexOfLabel(name) {
        for (var i = 0; i < pages.length; ++i) if (pages[i].label === name) return i
        return -1
    }
    function goTo(name) {
        for (var i = 0; i < pages.length; ++i) if (pages[i].label === name) { page = i; return }
    }
    onPageChanged: tools.setPage(pages[page].tool || "")

    // Nothing is prepared or animated while the window is hidden or minimized,
    // and the per-frame clock only runs on a page with moving charts.
    readonly property bool shown: visible && visibility !== Window.Minimized && visibility !== Window.Hidden
    onShownChanged: backend.setUiVisible(shown)
    Binding { target: Tr; property: "lang"; value: backend.settings.language || "en" }
    Binding { target: Clock; property: "active"; value: win.shown && win.pages[win.page].live === true }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0a0a0d" }
            GradientStop { position: 1.0; color: "#0b100e" }
        }
    }

    Rectangle {                         // sidebar
        id: side
        x: 16; y: 16; width: 212; height: parent.height - 32
        radius: Tokens.radius; color: Tokens.bg1
        border.width: 1; border.color: Tokens.line
        Text { x: 22; y: 22; text: "LMONITOR"; color: Tokens.text
               font.family: Tokens.font; font.pixelSize: 22; font.bold: true; font.letterSpacing: 1 }
        Rectangle { x: 22; y: 52; width: 28; height: 3; radius: 2; color: Tokens.accent }
        Column {
            x: 10; y: 70; width: parent.width - 20; spacing: 3
            Repeater {
                model: win.nav
                Item {
                    readonly property int pageIndex: modelData.label === undefined ? -1 : win.indexOfLabel(modelData.label)
                    width: parent.width; height: modelData.label === undefined ? (modelData.head === "" ? 8 : 24) : 40
                    Text { visible: modelData.label === undefined && modelData.head !== ""
                           x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 2
                           text: Tr.t(modelData.head); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
                    SideButton { visible: modelData.label !== undefined; width: parent.width; height: 40
                                 label: modelData.label || ""; active: win.page === parent.pageIndex
                                 onClicked: win.page = parent.pageIndex }
                }
            }
        }
        Card {
            x: 10; y: parent.height - 94; width: parent.width - 20; height: 84
            Text { x: 14; y: 14; color: backend.update.state === "available" ? Tokens.accent : Tokens.dim
                   text: backend.update.state === "available" ? Tr.t("Update available: ") + backend.update.version : Tr.t("Version")
                   font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                   font.bold: backend.update.state === "available"
                   MouseArea { anchors.fill: parent; enabled: backend.update.state === "available"
                               cursorShape: Qt.PointingHandCursor; onClicked: win.goTo("About") } }
            Text { x: 14; y: 32; text: backend.version; color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            Text { x: 14; y: 54; textFormat: Text.RichText; color: Tokens.dim
                   font.family: Tokens.font; font.pixelSize: 10
                   text: "<a href=\"https://github.com/unrealhamed/Lmonitor\" style=\"color:" + Tokens.accent + "\">GitHub</a>"
                   onLinkActivated: function (l) { Qt.openUrlExternally(l) } }
        }
    }

    Loader {
        id: content
        x: side.x + side.width + 20; y: 16
        width: parent.width - x - 20; height: parent.height - 32
        source: win.pages[win.page].src
    }
    Card {                                  // shown instead of a blank page when a page cannot load
        visible: content.status === Loader.Error
        x: content.x; y: content.y + 20; width: Math.min(content.width, 820); height: Math.min(content.height - 40, 420)
        Text { x: 20; y: 16; text: Tr.t("This page could not be loaded"); color: Tokens.danger
               font.family: Tokens.font; font.pixelSize: 18; font.bold: true }
        Text { x: 20; y: 50; width: parent.width - 40; height: parent.height - 66; wrapMode: Text.WrapAnywhere
               elide: Text.ElideRight; color: Tokens.sub; text: backend.qmlErrors || Tr.t("See the console window.")
               font.family: "Consolas"; font.pixelSize: 11 }
    }
}
