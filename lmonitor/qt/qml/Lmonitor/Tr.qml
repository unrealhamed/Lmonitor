pragma Singleton
import QtQuick
import "fa.js" as Fa

// The interface language. English text is the key; a text without a translation
// is shown in English, so a missing entry can never leave an empty label.
QtObject {
    property string lang: "en"
    function t(s) {
        if (s === undefined || s === null) return ""
        if (lang !== "fa") return s
        var v = Fa.strings[s]
        return v !== undefined ? v : s
    }
}
