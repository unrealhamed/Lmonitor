import QtQuick
import Lmonitor

Rectangle {
    property string status: "none"      // ok / warm / hot / high / low / full / none
    width: 8; height: 8; radius: 4
    color: status === "none" ? Tokens.dim : Tokens.statusColor(status)
}
