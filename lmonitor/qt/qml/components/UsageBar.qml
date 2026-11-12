import QtQuick
import Lmonitor
import "."                      // components/Text.qml: upright text in Persian

// "Utilization ......... 87%" with a thin bar. value null -> "--".
Item {
    id: root
    property string label: Tr.t("Utilization")
    property var value: null
    property color color: Tokens.text
    height: 34
    Text { text: root.label; color: Tokens.sub
           font.family: Tokens.font; font.pixelSize: Tokens.fsSmall }
    Text { anchors.right: parent.right
           text: root.value === null ? "--" : Math.round(root.value) + "%"
           color: Tokens.text; font.family: Tokens.font; font.pixelSize: Tokens.fsSmall; font.bold: true }
    Rectangle { y: 22; width: parent.width; height: 5; radius: 3; color: Tokens.track
        Rectangle { height: parent.height; radius: 3; color: root.color
                    width: root.value === null ? 0 : parent.width * Math.max(0, Math.min(100, root.value)) / 100
                    Behavior on width { NumberAnimation { duration: 250 } } } }
}
