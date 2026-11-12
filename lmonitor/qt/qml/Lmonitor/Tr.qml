pragma Singleton
import QtQuick
import "fa.js" as Fa

// The interface language. English text is the key; a text without a translation
// is shown in English, so a missing entry can never leave an empty label.
// Texts made by the engine with numbers in them ("Free space on C:") are matched by
// patterns (Fa.patterns); a long text that has no entry as a whole is translated
// sentence by sentence.
QtObject {
    property string lang: "en"
    readonly property bool rtl: lang === "fa"       // the main window is drawn right-to-left
    property int rev: 0                            // +1 when a part of the window turns itself back

    function one(s) {
        var v = Fa.strings[s]
        if (v !== undefined) return v
        for (var i = 0; i < Fa.patterns.length; ++i) {
            var p = Fa.patterns[i], m = s.match(p[0])
            if (!m) continue
            if (typeof p[1] === "function") {
                var self = this
                var tr = function (x) { if (x === undefined || x === "") return x || ""; var r = self.one(x); return r !== undefined ? r : x }
                return p[1].apply(null, [tr].concat(m.slice(1)))
            }
            return s.replace(p[0], p[1])
        }
        return undefined
    }
    // A Persian sentence with English words / numbers in it ("275 GB آزاد از 352 GB"):
    // the sentence is marked right-to-left, and every English / number group is kept in
    // one piece (Unicode isolates), so "275.3 GB" never shows as "GB 275.3".
    readonly property var _persian: /[\u0600-\u06FF]/
    readonly property var _ltrRun: /[A-Za-z0-9][A-Za-z0-9.,:\/+°%_\-]*(?:\s+[A-Za-z0-9.,:\/+°%_\-][A-Za-z0-9.,:\/+°%_\-]*)*/g
    function bidi(v) {
        if (!_persian.test(v) || v.charAt(0) === "\u200F") return v
        return "\u200F" + v.replace(_ltrRun, function (m) { return "\u2066" + m + "\u2069" })
    }
    // a whole line put together from pieces ("275 GB" + " free of " + "352 GB")
    function line(v) { return lang === "fa" && v ? bidi(String(v)) : v }
    function t(s) {
        if (s === undefined || s === null) return ""
        if (lang !== "fa") return s
        s = String(s)
        var r = tRaw(s)
        // a piece of a line (" free of ") stays as it is; the whole line is marked by line()
        return /^\s|\s$/.test(s) ? r : bidi(r)
    }
    function tRaw(s) {
        var v = one(s)
        if (v !== undefined) return v
        var lead = s.match(/^\s*/)[0], body = s.trim()   // keep indentation of row labels
        if (body !== s) {
            v = one(body)
            if (v !== undefined) return lead + v
        }
        // sentence by sentence (". " / " - " joins); untranslated parts stay English
        var parts = body.replace(/([.!?])\s+/g, "$1\u0001").split("\u0001")
        if (parts.length > 1) {
            var out = [], any = false
            for (var k = 0; k < parts.length; ++k) {
                var w = one(parts[k])
                if (w === undefined && /[.!?]$/.test(parts[k])) w = one(parts[k].slice(0, -1))
                any = any || w !== undefined
                out.push(w !== undefined ? w : parts[k])
            }
            if (any) return lead + out.join(" ")
        }
        return s
    }
    // Is this item drawn mirrored on screen (inside the right-to-left main window)?
    function mirrored(item) {
        if (!item) return false
        var a = item.mapToItem(null, 0, 0), b = item.mapToItem(null, 10, 0)
        return b.x < a.x
    }
}
