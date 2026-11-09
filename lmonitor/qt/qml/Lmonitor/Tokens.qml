pragma Singleton
import QtQuick

// Design tokens: every color, size and font of the interface lives here.
QtObject {
    // surfaces
    property color bg0: "#08080a"        // window
    property color bg1: "#0e0e11"        // sidebar
    property color card: "#131316"
    property color cardHi: "#1a1a1f"
    property color line: "#26262c"
    // text
    property color text: "#f4f4f6"
    property color sub: "#a0a0aa"
    property color dim: "#64646e"
    // accents (neon)
    readonly property color cyan: "#62c8ff"
    readonly property color blue: "#62c8ff"
    readonly property color violet: "#b48cff"
    readonly property color green: "#1fd18b"
    readonly property color orange: "#ffb04d"
    readonly property color warn: "#f5c542"
    readonly property color danger: "#ff5c6c"
    property color accent: green
    property bool light: false
    property color accentText: "#07130d"
    function fg(a) { return Qt.rgba(text.r, text.g, text.b, a) }
    function accentA(a) { return Qt.rgba(accent.r, accent.g, accent.b, a) }
    // metrics
    readonly property color cpu: blue
    readonly property color gpu: violet
    readonly property color ram: green
    readonly property color disk: orange
    // shape / type
    readonly property int radius: 16
    readonly property int gap: 14
    readonly property string font: "Segoe UI"
    readonly property int fsTitle: 26
    readonly property int fsHead: 15
    readonly property int fsBig: 34
    readonly property int fsBody: 13
    readonly property int fsSmall: 11

    function fmtNet(bps, unit) {        // the same text as the overlay (engine.fmt_net)
        if (bps === null || bps === undefined) return "--"
        if (unit === "bits") {
            var bits = bps * 8
            return bits >= 1e6 ? (bits / 1e6).toFixed(1) + "Mbps" : (bits / 1e3).toFixed(0) + "Kbps"
        }
        return bps >= 1048576 ? (bps / 1048576).toFixed(1) + "MB/s" : (bps / 1024).toFixed(0) + "KB/s"
    }
    function sevColor(s) {
        return s === "warn" ? danger : s === "notice" ? warn : s === "ok" ? green
             : s === "info" ? cyan : dim
    }
    function statusColor(s) {
        return s === "hot" || s === "high" || s === "full" ? danger
             : s === "warm" || s === "low" ? warn
             : s === "ok" ? green : dim
    }
    function statusText(s) {
        return Tr.t(({ok: "Optimal", warm: "Warm", hot: "Hot", high: "High load",
                      low: "Low space", full: "Almost full"})[s] || "No data")
    }
}
