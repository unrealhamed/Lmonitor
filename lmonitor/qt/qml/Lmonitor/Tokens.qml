pragma Singleton
import QtQuick

// Design tokens of the "Slate" design: every color, size and font of the window.
// Main.qml fills the mode colors from backend.ui (engine Theme.UI_SURFACES / UI_ACCENTS).
QtObject {
    // surfaces (dark mode values; light mode values come from the engine)
    property color bg0: "#0E1014"        // window background; also the inside of inputs
    property color bg1: "#15181D"        // sidebar
    property color card: "#15181D"       // cards
    property color cardHi: "#15181D"
    property color raised: "#232831"     // a selected segment, a secondary button (dark)
    property color line: "#252A32"       // hairline borders
    property color lineStrong: "#333944" // borders of controls, empty tracks
    // text
    property color text: "#ECEFF3"
    property color sub: "#A7AFBB"
    property color dim: "#737B89"
    // accent and states
    property color accent: "#2DD4A0"
    property color accentHover: "#4BE0B2"
    property color accentText: "#0B1015"
    property color warn: "#FBBF24"
    property color danger: "#F87171"
    property color info: "#60A5FA"
    property bool light: false
    // data colors (charts, cards): the same hues in both modes, deeper on white so they read
    readonly property color cyan: light ? "#0284C7" : "#62c8ff"
    readonly property color blue: cyan
    readonly property color violet: light ? "#7C3AED" : "#b48cff"
    readonly property color green: light ? "#059669" : "#1fd18b"
    readonly property color orange: light ? "#D97706" : "#ffb04d"
    readonly property color cpu: blue
    readonly property color gpu: violet
    readonly property color ram: green
    readonly property color disk: orange
    readonly property color track: lineStrong          // empty part of a bar or ring
    function fg(a) { return Qt.rgba(text.r, text.g, text.b, a) }
    function accentA(a) { return Qt.rgba(accent.r, accent.g, accent.b, a) }
    function tint(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
    // shape / type
    property int radius: 12
    readonly property int gap: 14
    readonly property var _families: Qt.fontFamilies()
    readonly property string font: _families.indexOf("Segoe UI Variable Text") >= 0 ? "Segoe UI Variable Text" : "Segoe UI"
    readonly property string fontDisplay: _families.indexOf("Segoe UI Variable Display") >= 0 ? "Segoe UI Variable Display" : "Segoe UI"
    // Windows' own icon font (Windows 11; Windows 10 has the same glyphs in MDL2)
    readonly property string iconFont: _families.indexOf("Segoe Fluent Icons") >= 0 ? "Segoe Fluent Icons" : "Segoe MDL2 Assets"
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
        return s === "warn" ? danger : s === "notice" ? warn : s === "ok" ? accent
             : s === "info" ? info : dim
    }
    function statusColor(s) {
        return s === "hot" || s === "high" || s === "full" ? danger
             : s === "warm" || s === "low" ? warn
             : s === "ok" ? accent : dim
    }
    function statusText(s) {
        return Tr.t(({ok: "Optimal", warm: "Warm", hot: "Hot", high: "High load",
                      low: "Low space", full: "Almost full"})[s] || "No data")
    }
}
