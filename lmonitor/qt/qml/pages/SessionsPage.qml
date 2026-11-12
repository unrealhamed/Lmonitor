import QtQuick
import Lmonitor
import "../components"

// Games are noticed automatically (a program drawing frames in front, seen by
// PresentMon); sessions of a minute or longer are saved on this PC.
Item {
    id: page
    readonly property var d: tools.sessions
    readonly property var items: d.items || []
    readonly property int g: Tokens.gap
    property int sel: -1
    property var detail: []

    onItemsChanged: {
        var ok = false
        for (var i = 0; i < items.length; ++i) if (items[i].id === sel) ok = true
        if (!ok) { sel = items.length ? items[0].id : -1 }
        reload()
    }
    onSelChanged: reload()
    function reload() { detail = sel >= 0 ? tools.sessionDetail(sel) : [] }

    PageHeader {
        id: head; width: parent.width
        kicker: page.d.status || ""; title: Tr.t("Sessions")
        Text { text: Tr.t("Record games"); color: Tokens.sub; anchors.verticalCenter: parent.verticalCenter
               font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
        ToggleSwitch { anchors.verticalCenter: parent.verticalCenter; checked: page.d.enabled === true
                       onToggled: function (v) { tools.sessionsOn(v) } }
    }

    Text { visible: page.items.length === 0; anchors.centerIn: parent; width: 440; wrapMode: Text.Wrap
           horizontalAlignment: Text.AlignHCenter; color: Tokens.dim; font.family: Tokens.font; font.pixelSize: 14
           text: Tr.t("No sessions yet. Play a game while Lmonitor is running - sessions of one minute or longer are saved here with FPS, 1% lows, temperatures and what slowed the game down.") }

    Card {                                                   // list
        id: listCard
        visible: page.items.length > 0
        y: head.height + 12; width: 330; height: parent.height - y
        ListView {
            anchors.fill: parent; anchors.margins: 10; clip: true; spacing: 6
            model: page.items; boundsBehavior: Flickable.StopAtBounds
            delegate: Rectangle {
                width: ListView.view.width; height: 66; radius: 12
                color: modelData.id === page.sel ? Tokens.accentA(0.16) : (ma.containsMouse ? Tokens.fg(0.05) : "transparent")
                border.width: modelData.id === page.sel ? 1 : 0; border.color: Tokens.accent
                Column { x: 14; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 28; spacing: 2
                    Text { width: parent.width; elide: Text.ElideRight; text: modelData.game + (modelData.live ? Tr.t("  ● recording") : "")
                           color: Tokens.text; font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                    Text { text: modelData.when + "  ·  " + modelData.duration; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 10 }
                    Text { color: Tokens.sub; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall
                           text: Tr.line((modelData.avg_fps !== null && modelData.avg_fps !== undefined ? Math.round(modelData.avg_fps) + Tr.t(" FPS avg") : Tr.t("FPS n/a"))
                                 + (modelData.low1 !== null && modelData.low1 !== undefined ? Tr.t("  ·  1% low ") + Math.round(modelData.low1) : "")) } }
                MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: page.sel = modelData.id }
            }
        }
    }

    Flickable {                                              // details
        visible: page.items.length > 0
        x: 330 + page.g; y: head.height + 12; width: parent.width - x; height: parent.height - y
        contentWidth: width; contentHeight: dcol.height + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds
        Column {
            id: dcol; width: parent.width - 8; spacing: page.g
            Repeater { model: page.detail
                       RowsCard { width: dcol.width; title: modelData.title; rows: modelData.rows } }
            ConfirmButton { visible: page.sel >= 0; danger: true; label: Tr.t("Delete this session"); question: Tr.t("Delete it?")
                            onConfirmed: tools.sessionDelete(page.sel) }
        }
    }
}
