import QtQuick as Q
import Lmonitor

// Every page's Text (this file replaces QtQuick's Text for the "components" import).
// In Persian the main window is drawn mirrored (right-to-left); a text there turns
// itself back so it reads normally, and its left / right alignment is swapped (a row
// starts on the right). Elsewhere (overlay windows) it is a plain Text.
Q.Text {
    id: t
    horizontalAlignment: Q.Text.AlignLeft          // "start"; swapped to the right in Persian
    property bool upright: false
    property int lmOrigAlign: -1                   // the alignment before the swap
    function lmApply(on) {
        if (on === t.upright) return
        t.upright = on
        if (on) {
            t.lmOrigAlign = t.horizontalAlignment
            if (t.horizontalAlignment === Q.Text.AlignLeft) t.horizontalAlignment = Q.Text.AlignRight
            else if (t.horizontalAlignment === Q.Text.AlignRight) t.horizontalAlignment = Q.Text.AlignLeft
        } else if (t.lmOrigAlign >= 0) {
            t.horizontalAlignment = t.lmOrigAlign
            t.lmOrigAlign = -1
        }
    }
    // checked a moment later (after the parents are placed); a text that was removed in
    // the meantime (lists rebuild their rows) is skipped
    function lmDirLater() {
        if (!Tr.rtl && !t.upright) return               // English: nothing to do
        Qt.callLater(function () {
            // a text being deleted (a list row rebuilt) has lost its functions: skip it
            if (t && typeof t.lmApply === "function" && t.parent !== null && t.parent !== undefined)
                t.lmApply(Tr.rtl && Tr.mirrored(t.parent))
        })
    }
    transform: Q.Scale { origin.x: t.width / 2; xScale: t.upright ? -1 : 1 }
    Q.Component.onCompleted: t.lmDirLater()
    onParentChanged: t.lmDirLater()
    property Q.Connections _lmLang: Q.Connections {
        target: Tr
        function onLangChanged() { t.lmDirLater() }
        function onRevChanged() { t.lmDirLater() }
    }
}
