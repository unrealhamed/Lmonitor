import QtQuick
import Lmonitor
import "../components"

// What takes space. Cleaning is limited to known cache / temp folders (files
// older than a day, never anything through a link) and single large files go to
// the Recycle Bin. Everything else is only measured.
Item {
    id: page
    readonly property var d: tools.storage
    readonly property bool busy: d.busy === true
    readonly property int g: Tokens.gap
    property var sel: ({})                       // cache id -> ticked
    property bool seeded: false

    function seed() {
        if (seeded || !d.caches || d.caches.length === 0 || !d.scanned) return
        var m = {}
        for (var i = 0; i < d.caches.length; ++i) m[d.caches[i].id] = d.caches[i].recommended && d.caches[i].present
        sel = m; seeded = true
    }
    onDChanged: seed()
    function picked() { var r = []; for (var k in sel) if (sel[k]) r.push(k); return r }
    function pickedBytes() {
        var b = 0, c = d.caches || []
        for (var i = 0; i < c.length; ++i) if (sel[c[i].id]) b += c[i].old_bytes
        return b
    }
    function fmt(b) { return b >= 1073741824 ? (b / 1073741824).toFixed(1) + " GB" : b >= 1048576 ? (b / 1048576).toFixed(0) + " MB" : Math.round(b / 1024) + " KB" }

    PageHeader {
        id: head; width: parent.width
        kicker: page.busy ? (page.d.progress ? "Scanning " + page.d.progress : "Working…") : "Find what takes space and clean safely"
        title: "Storage"
        Pill { label: "Re-scan"; onClicked: if (!page.busy) tools.storScanCaches() }
    }
    ResultBanner { id: banner; y: head.height + 8; width: parent.width
                   result: page.d.last; onDismissed: tools.storDismiss() }

    Flickable {
        y: head.height + 8 + (banner.visible ? banner.height + page.g : 0)
        width: parent.width; height: parent.height - y
        contentWidth: width; contentHeight: body.height + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds
        Column {
            id: body; width: parent.width - 8; spacing: page.g

            Flow {                                           // drives
                width: parent.width; spacing: page.g
                Repeater {
                    model: page.d.drives || []
                    Card {
                        width: Math.min(300, (body.width - 2 * page.g) / 3); height: 92
                        Text { x: 18; y: 14; text: modelData.mount + (modelData.label ? "  " + modelData.label : ""); color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: 15; font.bold: true }
                        Text { x: 18; y: 38; text: modelData.free + " free of " + modelData.total; color: Tokens.sub
                               font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                        Rectangle { x: 18; y: 66; width: parent.width - 36; height: 6; radius: 3; color: "#2a2a31"
                            Rectangle { height: parent.height; radius: 3; width: parent.width * Math.min(100, modelData.pct) / 100
                                        color: modelData.pct > 90 ? Tokens.danger : modelData.pct > 80 ? Tokens.warn : Tokens.accent } }
                    }
                }
            }

            Card {                                           // caches
                width: parent.width; height: cc.height + 36
                Column {
                    id: cc; x: 20; y: 16; width: parent.width - 40; spacing: 6
                    Item { width: parent.width; height: 30
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "Cache and temp folders"; color: Tokens.text
                               font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                        Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                               text: page.d.scanned ? "Can free about " + page.d.reclaimable : ""; color: Tokens.accent
                               font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true } }
                    Repeater {
                        model: page.d.caches || []
                        Item {
                            width: parent.width; height: 48
                            Rectangle { visible: index > 0; width: parent.width; height: 1; color: "#1e1e23" }
                            Check { anchors.verticalCenter: parent.verticalCenter; visible: modelData.present
                                    checked: !!page.sel[modelData.id]
                                    onToggled: function (v) { var m = {}; for (var k in page.sel) m[k] = page.sel[k]; m[modelData.id] = v; page.sel = m } }
                            Column { x: 36; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 170; spacing: 1
                                Text { width: parent.width; elide: Text.ElideRight; text: modelData.title
                                       color: modelData.present ? Tokens.text : Tokens.dim
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                                Text { width: parent.width; elide: Text.ElideRight; text: modelData.note; color: Tokens.dim
                                       font.family: Tokens.font; font.pixelSize: 10 } }
                            Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                   horizontalAlignment: Text.AlignRight
                                   text: !modelData.scanned ? "…" : !modelData.present ? "not found" : modelData.old + " old\n(" + modelData.all + " total)"
                                   color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                        }
                    }
                    Item { width: parent.width; height: 52
                        Text { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 220; wrapMode: Text.Wrap
                               text: "Only files older than a day are removed. This cannot be undone; the folders are rebuilt as needed."
                               color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 10 }
                        ConfirmButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; primary: true
                                        label: "Clean selected (" + page.fmt(page.pickedBytes()) + ")"
                                        ready: !page.busy && page.picked().length > 0
                                        question: "Delete old files?"
                                        onConfirmed: tools.storClean(page.picked()) } }
                }
            }

            Card {                                           // big folders / large files
                width: parent.width; height: bc.height + 36
                Column {
                    id: bc; x: 20; y: 16; width: parent.width - 40; spacing: 8
                    Text { text: "Big folders and large files"; color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Text { width: parent.width; wrapMode: Text.Wrap; color: Tokens.dim
                           text: "Measuring only. Windows, Program Files and system folders are never offered for deletion."
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    Row { spacing: 10
                        Pill { label: "Find big folders"; onClicked: if (!page.busy) tools.storScanFolders() }
                        Pill { label: "Find large files (500 MB+)"; onClicked: if (!page.busy) tools.storScanLarge() } }
                    Text { visible: page.d.folders_done && (page.d.folders || []).length > 0; text: "BIGGEST FOLDERS"; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: 10; font.bold: true }
                    Repeater {
                        model: page.d.folders || []
                        Item { width: parent.width; height: 36
                            Text { width: parent.width - 220; anchors.verticalCenter: parent.verticalCenter; elide: Text.ElideMiddle
                                   text: modelData.path; color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                            Text { anchors.right: showBtn.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                   text: modelData.size + (modelData.partial ? "+" : ""); color: Tokens.accent
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                            Pill { id: showBtn; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; height: 28
                                   label: "Show"; onClicked: tools.storShow(modelData.path) } }
                    }
                    Text { visible: page.d.large_done && (page.d.large || []).length > 0; text: "LARGE FILES"; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: 10; font.bold: true }
                    Text { visible: page.d.large_done && (page.d.large || []).length === 0; text: "No file of 500 MB or more was found."; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Repeater {
                        model: page.d.large || []
                        Item { width: parent.width; height: 50
                            Column { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 330; spacing: 1
                                Text { width: parent.width; elide: Text.ElideMiddle; text: modelData.path; color: Tokens.text
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                                Text { visible: modelData.reason !== ""; width: parent.width; elide: Text.ElideRight; text: modelData.reason
                                       color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 10 } }
                            Text { anchors.right: row2.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                                   text: modelData.size; color: Tokens.accent
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                            Row { id: row2; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; spacing: 8
                                Pill { label: "Show"; height: 28; onClicked: tools.storShow(modelData.path) }
                                ConfirmButton { visible: modelData.deletable; label: "Recycle"; question: "Move to Recycle Bin?"
                                                ready: !page.busy; onConfirmed: tools.storRecycle(modelData.path) } } }
                    }
                }
            }
        }
    }
}
