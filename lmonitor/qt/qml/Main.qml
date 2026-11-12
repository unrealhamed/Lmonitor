import QtQuick
import QtQuick.Window
import Lmonitor
import "components"
import "pages"

Window {
    id: win
    // "Interface size" (Personalize) makes everything bigger or smaller: the content is
    // laid out on a smaller / larger sheet and scaled to the window.
    readonly property real zoom: backend.ui.zoom || 1
    width: 1320; height: 820
    minimumWidth: Math.min(1120 * zoom, Screen.desktopAvailableWidth - 40)
    minimumHeight: Math.min(760 * zoom, Screen.desktopAvailableHeight - 60)
    visible: !backend.startHidden          // started by Windows: tray only
    title: "Lmonitor"
    color: Tokens.bg0

    property int page: 0
    Repeater {                              // the chosen app theme drives the shared tokens
        model: ["bg0", "bg1", "card", "cardHi", "line", "text", "sub", "dim", "accent", "light", "accentText", "radius", "font"]
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
        {label: "Graph overlay", src: "pages/HudPage.qml"},
        {label: "Sessions", src: "pages/SessionsPage.qml", tool: "sessions"},
        {head: "TOOLS"},
        {label: "Optimizer", src: "pages/OptimizerPage.qml", tool: "opt"},
        {label: "Storage", src: "pages/StoragePage.qml", tool: "storage"},
        {label: "PC check", src: "pages/ReportsPage.qml", tool: "reports"},
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
    // a full-screen game in front: no animation at all (the window can't be seen anyway)
    Binding { target: Clock; property: "active"; value: win.shown && !backend.covered && win.pages[win.page].live === true }

    // Persian: the whole window is drawn mirrored (sidebar on the right, rows from the
    // right); every Text turns itself back (components/Text.qml), charts keep time
    // running left to right.
    Item {
    id: stage
    width: win.width / win.zoom; height: win.height / win.zoom
    transform: [Scale { origin.x: stage.width / 2; xScale: Tr.rtl ? -1 : 1 },
                Scale { xScale: win.zoom; yScale: win.zoom }]

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Tokens.bg0 }      // was a fixed dark color: themes
            GradientStop { position: 1.0; color: Qt.tint(Tokens.bg0, Tokens.accentA(0.035)) }   // did not reach it
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
                    width: parent.width; height: modelData.label === undefined ? (modelData.head === "" ? 8 : 24) : 36
                    Text { visible: modelData.label === undefined && modelData.head !== ""
                           x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 2
                           text: Tr.t(modelData.head); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
                    SideButton { visible: modelData.label !== undefined; width: parent.width; height: 36
                                 label: modelData.label || ""; active: win.page === parent.pageIndex
                                 onClicked: win.page = parent.pageIndex }
                }
            }
        }
        Card {
            x: 10; y: parent.height - 94; width: parent.width - 20; height: 84
            Text { x: 14; y: 14; color: backend.update.state === "available" ? Tokens.accent : Tokens.dim
                   text: backend.update.state === "available" ? Tr.line(Tr.t("Update available: ") + backend.update.version) : Tr.t("Version")
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
    // A new version: shown on every page until installed or "Later" (comes back for the
    // next version, or after a restart).
    property string laterVersion: ""
    Rectangle {
        id: updBar
        readonly property bool on: backend.update.state === "available" && backend.update.version !== win.laterVersion
        visible: on
        z: 10
        x: content.x; y: stage.height - height - 16
        width: content.width; height: 56; radius: Tokens.radius
        color: Tokens.cardHi; border.width: 1; border.color: Tokens.accent
        Rectangle { x: 18; anchors.verticalCenter: parent.verticalCenter; width: 10; height: 10; radius: 5; color: Tokens.accent }
        Text { x: 40; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 330; elide: Text.ElideRight
               text: Tr.line(Tr.t("A new version is available: ") + (backend.update.version || ""))
               color: Tokens.text; font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
        Row {
            anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; spacing: 8
            Pill { primary: true; label: Tr.t("Install now"); onClicked: backend.installUpdate() }
            Pill { label: Tr.t("Later"); onClicked: win.laterVersion = backend.update.version }
        }
    }
    Rectangle {                              // while it downloads
        visible: backend.update.state === "downloading"
        z: 10; x: content.x; y: stage.height - height - 16
        width: content.width; height: 56; radius: Tokens.radius
        color: Tokens.cardHi; border.width: 1; border.color: Tokens.accent
        Text { x: 22; anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Downloading...")
               color: Tokens.text; font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
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
}
