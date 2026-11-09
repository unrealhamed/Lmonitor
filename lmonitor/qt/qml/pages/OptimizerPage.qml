import QtQuick
import Lmonitor
import "../components"

// Safe, reversible changes only. Every change is logged and can be undone in
// History. Not offered on purpose: disabling services, registry cleaners,
// overclocking.
Item {
    id: page
    readonly property var o: tools.opt
    readonly property int g: Tokens.gap
    readonly property real colW: (width - g) / 2
    readonly property bool busy: o.busy === true

    PageHeader {
        id: head; width: parent.width
        kicker: Tr.t("Every change can be undone"); title: Tr.t("Optimizer")
        Pill { label: page.busy ? Tr.t("Working…") : Tr.t("Refresh"); onClicked: if (!page.busy) tools.optRefresh() }
    }
    ResultBanner { id: banner; y: head.height + 8; width: parent.width
                   result: page.o.last; onDismissed: tools.optDismiss() }

    Flickable {
        id: flick
        y: head.height + 8 + (banner.visible ? banner.height + page.g : 0)
        width: parent.width; height: parent.height - y
        contentWidth: width; contentHeight: Math.max(colA.height, colB.height) + 8
        clip: true; boundsBehavior: Flickable.StopAtBounds

        Column {
            id: colA; width: page.colW; spacing: page.g
            Card {                                           // presets
                width: parent.width; height: pCol.height + 36
                Column {
                    id: pCol; x: 20; y: 16; width: parent.width - 40; spacing: 14
                    Text { text: Tr.t("Quick presets"); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Repeater {
                        model: page.o.presets || []
                        Column {
                            width: parent.width; spacing: 6
                            Item { width: parent.width; height: 38
                                Text { anchors.verticalCenter: parent.verticalCenter; text: Tr.t(modelData.title); color: Tokens.accent
                                       font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                                ConfirmButton { anchors.right: parent.right; label: Tr.t("Apply"); ready: !page.busy && modelData.steps.length > 0
                                                question: Tr.t("Apply ") + modelData.steps.length + Tr.t(" change(s)?")
                                                onConfirmed: tools.optPreset(modelData.name) } }
                            Repeater { model: modelData.steps
                                Text { width: parent.width; wrapMode: Text.Wrap; text: "•  " + modelData; color: Tokens.sub
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody } }
                            Text { visible: modelData.steps.length === 0; text: Tr.t("Already set - nothing to change."); color: Tokens.dim
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                            Text { visible: modelData.note !== ""; width: parent.width; wrapMode: Text.Wrap; text: Tr.t(modelData.note)
                                   color: Tokens.warn; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                        }
                    }
                }
            }
            Card {                                           // game settings
                width: parent.width; height: gCol.height + 36
                Column {
                    id: gCol; x: 20; y: 16; width: parent.width - 40; spacing: 14
                    Text { text: Tr.t("Windows game settings"); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Repeater {
                        model: page.o.settings || []
                        Item {
                            width: parent.width; height: 52
                            Column { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 150; spacing: 2
                                Text { text: Tr.t(modelData.title); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 14; font.bold: true }
                                Text { width: parent.width; wrapMode: Text.Wrap; text: Tr.t(modelData.sub); color: Tokens.dim
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsSmall } }
                            Text { visible: modelData.good; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                   text: "✓ " + Tr.t(modelData.text); color: Tokens.accent
                                   font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                            ConfirmButton { visible: !modelData.good; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                            label: modelData.button; ready: !page.busy; question: Tr.t("Change it?")
                                            onConfirmed: tools.optSetting(modelData.sid) }
                        }
                    }
                }
            }
            Card {                                           // power plan
                width: parent.width; height: plCol.height + 36
                Column {
                    id: plCol; x: 20; y: 16; width: parent.width - 40; spacing: 12
                    Text { text: Tr.t("Power plan"); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Text { visible: !page.o.plans_ok; text: Tr.t("Windows did not list its power plans."); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Repeater {
                        model: page.o.plans || []
                        Item {
                            width: parent.width; height: 40
                            Rectangle { y: 14; width: 12; height: 12; radius: 6; color: modelData.active ? Tokens.accent : "transparent"
                                        border.width: 1; border.color: modelData.active ? Tokens.accent : Tokens.line }
                            Text { x: 24; anchors.verticalCenter: parent.verticalCenter; text: Tr.t(modelData.name); color: Tokens.text
                                   font.family: Tokens.font; font.pixelSize: 14; font.bold: modelData.active }
                            ConfirmButton { visible: !modelData.active; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                            label: Tr.t("Use"); ready: !page.busy; question: Tr.t("Switch plan?")
                                            onConfirmed: tools.optPower(modelData.guid) }
                        }
                    }
                }
            }
        }

        Column {
            id: colB; x: page.colW + page.g; width: page.colW; spacing: page.g
            Card {                                           // startup
                width: parent.width; height: sCol.height + 36
                Column {
                    id: sCol; x: 20; y: 16; width: parent.width - 40; spacing: 8
                    Text { text: Tr.t("Startup programs"); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Text { width: parent.width; wrapMode: Text.Wrap; color: Tokens.dim
                           text: Tr.t("Switching one off only stops it from starting with Windows. Nothing is deleted.")
                           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
                    Text { visible: (page.o.startup || []).length === 0; text: Tr.t("No startup programs found."); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Repeater {
                        model: page.o.startup || []
                        Item {
                            width: parent.width; height: 46
                            Rectangle { visible: index > 0; width: parent.width; height: 1; color: "#1e1e23" }
                            Column { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 70; spacing: 1
                                Text { width: parent.width; elide: Text.ElideRight; text: Tr.t(modelData.name); color: modelData.enabled ? Tokens.text : Tokens.dim
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                                Text { width: parent.width; elide: Text.ElideMiddle; text: modelData.where + "  ·  " + modelData.cmd; color: Tokens.dim
                                       font.family: Tokens.font; font.pixelSize: 10 } }
                            ToggleSwitch { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                           checked: modelData.enabled
                                           onToggled: function (v) { if (!page.busy) tools.optStartup(modelData.key, v) } }
                        }
                    }
                }
            }
            Card {                                           // history
                width: parent.width; height: hCol.height + 36
                Column {
                    id: hCol; x: 20; y: 16; width: parent.width - 40; spacing: 8
                    Text { text: Tr.t("History"); color: Tokens.text; font.family: Tokens.font; font.pixelSize: 16; font.bold: true }
                    Text { visible: (page.o.history || []).length === 0; text: Tr.t("Nothing changed yet."); color: Tokens.dim
                           font.family: Tokens.font; font.pixelSize: Tokens.fsBody }
                    Repeater {
                        model: page.o.history || []
                        Item {
                            width: parent.width; height: 54
                            Rectangle { visible: index > 0; width: parent.width; height: 1; color: "#1e1e23" }
                            Column { anchors.verticalCenter: parent.verticalCenter; width: parent.width - 90; spacing: 1
                                Text { width: parent.width; elide: Text.ElideRight; text: Tr.t(modelData.title); color: Tokens.text
                                       font.family: Tokens.font; font.pixelSize: Tokens.fsBody; font.bold: true }
                                Text { width: parent.width; elide: Text.ElideRight; color: Tokens.dim
                                       text: modelData.when + "  ·  " + Tr.t(modelData.status)
                                       font.family: Tokens.font; font.pixelSize: 10 } }
                            Pill { visible: modelData.undo; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                                   label: Tr.t("Undo"); height: 30; onClicked: if (!page.busy) tools.optUndo(modelData.id) }
                        }
                    }
                }
            }
        }
    }
}
