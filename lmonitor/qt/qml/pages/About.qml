import QtQuick
import QtQuick.Window
import Lmonitor
import "../components"

Item {
    id: page
    PageHeader { id: head; width: parent.width; kicker: Tr.t("Gaming overlay and system monitor"); title: Tr.t("About") }
    Card {
        id: infoCard
        y: head.height + 12; width: Math.min(parent.width, 720); height: col.height + 44; tint: true
        Column {
            id: col
            x: 24; y: 22; width: parent.width - 48; spacing: 14
            Text { text: "Lmonitor"; color: Tokens.text
                   font.family: Tokens.font; font.pixelSize: 26; font.bold: true }
            Text { text: Tr.line(Tr.t("Version ") + backend.version); color: Tokens.accent
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 14; lineHeight: 1.25
                   text: Tr.t("Lmonitor is a overly and system monitor for windows. It shows FPS, CPU, RAM, and net reading on top of your programs, and keep a record of your program sessions.") }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 14; lineHeight: 1.25
                   text: Tr.t("Made by a Claude and new developer named unrealhamed.") }
            Text { textFormat: Text.RichText; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: 14
                   text: "GitHub: <a href=\"https://github.com/unrealhamed/Lmonitor\" style=\"color:" + Tokens.accent + "\">github.com/unrealhamed/Lmonitor</a>"
                   onLinkActivated: function (l) { Qt.openUrlExternally(l) }
                   MouseArea { anchors.fill: parent; acceptedButtons: Qt.NoButton
                               cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor } }
            Row {
                spacing: 12
                Pill { label: backend.update.state === "checking" ? Tr.t("Checking...") : Tr.t("Check for updates")
                       onClicked: backend.checkUpdate() }
                Pill { visible: !!backend.whatsNewLatest.slides; label: Tr.t("What's new")
                       onClicked: Window.window.showWhatsNew() }
                Pill { visible: backend.update.state === "available"; primary: true
                       label: Tr.line(Tr.t("Download and install ") + backend.update.version)
                       onClicked: backend.installUpdate() }
                Text { anchors.verticalCenter: parent.verticalCenter; color: Tokens.sub
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                       text: ({available: Tr.t("A new version is available"), none: Tr.t("You have the latest version"),
                               downloading: Tr.t("Downloading..."), ready: Tr.t("Installing - Lmonitor will restart"),
                               error: Tr.line(Tr.t("Could not check: ") + (backend.update.text || ""))})[backend.update.state] || "" }
            }
            Rectangle {                     // what the new version changes (the release's own text)
                visible: backend.update.state === "available" && !!backend.update.notes
                width: parent.width; height: visible ? notesCol.height + 24 : 0; radius: 10
                color: Tokens.bg0; border.width: 1; border.color: Tokens.line
                Column { id: notesCol; x: 14; y: 12; width: parent.width - 28; spacing: 6
                    Text { text: Tr.line(Tr.t("What's in version ") + (backend.update.version || "")); color: Tokens.text
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                    Text { width: parent.width; wrapMode: Text.WordWrap; text: backend.update.notes || ""; color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; lineHeight: 1.2 }
                    Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: 11
                           text: Tr.t("The installer is checked (size and SHA-256) before it runs. If anything fails, your current version stays as it is.") } }
            }
        }
    }

    Card {                                  // ---- privacy: what Lmonitor keeps and sends
        id: priv
        property bool open: false
        property bool cleared: false
        y: infoCard.y + infoCard.height + Tokens.gap
        width: Math.min(parent.width, 720); height: pCol.height + 36
        Column {
            id: pCol; x: 24; y: 18; width: parent.width - 48; spacing: 10
            Item { width: parent.width; height: 24
                Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t("Your data and privacy"); color: Tokens.text
                       font.family: Tokens.font; font.pixelSize: Tokens.fsHead; font.weight: Font.DemiBold }
                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                       text: priv.open ? Tr.t("Hide") : Tr.t("Show"); color: Tokens.accent
                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                       MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: priv.open = !priv.open } } }
            Text { width: parent.width; wrapMode: Text.WordWrap; color: Tokens.sub
                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody
                   text: Tr.t("Everything Lmonitor measures stays on this PC. There is no account, no cloud and no usage tracking.") }
            Column {
                visible: priv.open; width: parent.width; spacing: 8
                Repeater {
                    model: [
                        "Settings, your game sessions, PC check results, the Optimizer's list of changes, your own network count and an error log are kept in %APPDATA%\\Lmonitor. Delete that folder and they are gone.",
                        "Game sessions hold the game's file name, times, frame rates, temperatures, load and the names of busy background programs - nothing from inside the game.",
                        "Internet: only GitHub, to look for a new version (at start and every 3 hours) and to download it when you press Install. Nothing about you or your PC is sent.",
                        "Lmonitor reads frame times with Microsoft's PresentMon and sensors with LibreHardwareMonitor. It never injects anything into a game.",
                        "The Optimizer changes nothing without asking, and every change it makes can be undone in its History."
                    ]
                    Text { width: pCol.width; wrapMode: Text.WordWrap; text: "•  " + Tr.t(modelData); color: Tokens.sub
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; lineHeight: 1.15 }
                }
                Row { spacing: 10
                    Pill { label: Tr.t("Open the data folder"); onClicked: backend.openDataFolder() }
                    ConfirmButton { danger: true; label: Tr.t("Delete my history")
                                    question: Tr.t("Delete game sessions, PC check results and network counts?")
                                    onConfirmed: { backend.clearHistory(); priv.cleared = true } } }
                Text { visible: priv.cleared; text: Tr.t("Deleted. Your settings were kept."); color: Tokens.accent
                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
            }
        }
    }
}
