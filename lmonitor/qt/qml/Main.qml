import QtQuick
import QtQuick.Window
import QtQuick.Effects
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
    Repeater {                              // light / dark mode + accent drive the shared tokens
        model: ["bg0", "bg1", "card", "cardHi", "raised", "line", "lineStrong", "text", "sub", "dim",
                "accent", "accentHover", "accentText", "warn", "danger", "info", "light"]
        Item { Binding { target: Tokens; property: modelData
                         value: backend.ui[modelData]
                         when: backend.ui[modelData] !== undefined } }
    }
    // header rows have no page; the rest are pages in this order
    readonly property var nav: [
        {head: "MAIN"},
        {label: "Home", icon: "\uE80F", src: "pages/Dashboard.qml", live: true},
        {label: "Graphs", icon: "\uE9D2", src: "pages/GraphsPage.qml", live: true},
        {label: "Hardware", icon: "\uE950", src: "pages/HardwarePage.qml"},
        {label: "Network usage", icon: "\uE8CB", src: "pages/NetUsagePage.qml", hidden: true},   // from Home > Network
        {head: "GAMING"},
        {label: "Overlay", icon: "\uE7F4", src: "pages/OverlayPage.qml"},
        {label: "Graph overlay", icon: "\uE9D9", src: "pages/HudPage.qml"},
        {label: "Sessions", icon: "\uE7FC", src: "pages/SessionsPage.qml", tool: "sessions"},
        {head: "TOOLS"},
        {label: "Optimizer", icon: "\uE9E9", src: "pages/OptimizerPage.qml", tool: "opt"},
        {label: "Storage", icon: "\uEDA2", src: "pages/StoragePage.qml", tool: "storage"},
        {label: "PC check", icon: "\uEA18", src: "pages/ReportsPage.qml", tool: "reports"},
        {head: ""},
        {label: "Personalize", icon: "\uE790", src: "pages/PersonalizePage.qml"},
        {label: "About", icon: "\uE946", src: "pages/About.qml"}
    ]
    readonly property var pages: nav.filter(function (n) { return n.label !== undefined })
    function indexOfLabel(name) {
        for (var i = 0; i < pages.length; ++i) if (pages[i].label === name) return i
        return -1
    }
    function goTo(name) {
        for (var i = 0; i < pages.length; ++i) if (pages[i].label === name) { page = i; return }
    }
    onPageChanged: {
        tools.setPage(pages[page].tool || "")
        if (pages[page].live !== true) backend.setGraphFast(false)   // no real-time chart on this page
    }

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
    // "What's new": once after an update that added something; again from About
    property var wnInfo: backend.whatsNew
    property bool wnDone: false
    readonly property bool wnOpen: shown && !wnDone && !!wnInfo.slides && wnInfo.slides.length > 0
    function showWhatsNew() { wnInfo = backend.whatsNewLatest; wnDone = false }

    Item {
    id: stage
    width: win.width / win.zoom; height: win.height / win.zoom
    // the window goes out of focus (blurred) behind the What's new box; not with the
    // software renderer, which cannot draw effects
    property real blurAmount: win.wnOpen ? 1 : 0
    Behavior on blurAmount { NumberAnimation { duration: 260 } }
    layer.enabled: blurAmount > 0 && GraphicsInfo.api !== GraphicsInfo.Software
    layer.effect: MultiEffect { blurEnabled: true; blurMax: 40; blur: stage.blurAmount }
    transform: [Scale { origin.x: stage.width / 2; xScale: Tr.rtl ? -1 : 1 },
                Scale { xScale: win.zoom; yScale: win.zoom }]

    Rectangle { anchors.fill: parent; color: Tokens.bg0 }

    Rectangle {                         // sidebar: the full height, a hairline to the content
        id: side
        x: 0; y: 0; width: 228; height: parent.height
        color: Tokens.bg1
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Tokens.line }
        Row {
            x: 22; y: 22; spacing: 10
            Rectangle { width: 28; height: 28; radius: 8; color: Tokens.accent
                        Text { anchors.centerIn: parent; text: "\uE9D9"; color: Tokens.accentText
                               font.family: Tokens.iconFont; font.pixelSize: 16 } }
            Text { anchors.verticalCenter: parent.verticalCenter; text: "Lmonitor"; color: Tokens.text
                   font.family: Tokens.fontDisplay; font.pixelSize: 18; font.weight: Font.DemiBold }
        }
        Column {
            x: 12; y: 66; width: parent.width - 24; spacing: 2
            Repeater {
                model: win.nav
                Item {
                    readonly property int pageIndex: modelData.label === undefined ? -1 : win.indexOfLabel(modelData.label)
                    width: parent.width; height: modelData.hidden ? 0 : modelData.label === undefined ? (modelData.head === "" ? 10 : 28) : 36
                    visible: !modelData.hidden
                    Text { visible: modelData.label === undefined && modelData.head !== ""
                           x: 10; anchors.bottom: parent.bottom; anchors.bottomMargin: 6
                           text: Tr.t(modelData.head); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.6 }
                    SideButton { visible: modelData.label !== undefined; width: parent.width; height: 36
                                 label: modelData.label || ""; icon: modelData.icon || ""
                                 active: win.page === parent.pageIndex
                                 onClicked: win.page = parent.pageIndex }
                }
            }
        }
        Item {                          // version line (a new version: says so, opens About)
            x: 12; y: parent.height - 46; width: parent.width - 24; height: 46
            Rectangle { width: parent.width; height: 1; color: Tokens.line }
            Text { x: 10; anchors.verticalCenter: parent.verticalCenter
                   text: backend.update.state === "available" ? Tr.line(Tr.t("Update available: ") + backend.update.version)
                                                              : Tr.line(Tr.t("Version ") + backend.version)
                   color: backend.update.state === "available" ? Tokens.accent : Tokens.dim
                   font.family: Tokens.font; font.pixelSize: 12
                   font.weight: backend.update.state === "available" ? Font.DemiBold : Font.Normal
                   MouseArea { anchors.fill: parent; enabled: backend.update.state === "available"
                               cursorShape: Qt.PointingHandCursor; onClicked: win.goTo("About") } }
            Text { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                   text: "GitHub"; color: ghMouse.containsMouse ? Tokens.accentHover : Tokens.accent
                   font.family: Tokens.font; font.pixelSize: 12; font.weight: Font.DemiBold
                   MouseArea { id: ghMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                               onClicked: Qt.openUrlExternally("https://github.com/unrealhamed/Lmonitor") } }
        }
    }

    Loader {
        id: content
        x: side.width + 28; y: 22
        width: parent.width - x - 28; height: parent.height - 44
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
        color: Tokens.card; border.width: 1; border.color: Tokens.accentA(0.6)
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
        color: Tokens.card; border.width: 1; border.color: Tokens.accentA(0.6)
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
    WhatsNew {
        width: win.width / win.zoom; height: win.height / win.zoom
        transform: Scale { xScale: win.zoom; yScale: win.zoom }
        info: win.wnInfo
        open: win.wnOpen
        onClosed: { win.wnDone = true; backend.whatsNewDone() }
    }
}
