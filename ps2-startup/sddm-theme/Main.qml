// PS2 XFCE -- SDDM greeter (Qt6)
// The background is the exact final frame of ps2_xfce_startup.mp4, so the boot
// animation hands over to this screen without a visible cut. The only way past
// it is a successful PAM login (sddm.login) or the power buttons.
import QtQuick
import QtQuick.Controls.Basic

Item {
    id: root
    width: 1920
    height: 1080

    readonly property real sx: width / 1920
    readonly property real sy: height / 1080
    readonly property color accent: "#5fb4ff"
    readonly property color dim: "#8fa3bd"
    readonly property string userName: config.stringValue("user") !== "" ? config.stringValue("user") : userModel.lastUser
    property int sessionIndex: sessionModel.lastIndex
    property bool busy: false

    function doLogin() {
        if (busy)
            return
        if (password.text.length === 0) {
            status.show("ENTER YOUR PASSWORD", dim)
            return
        }
        busy = true
        status.show("AUTHENTICATING…", accent)
        sddm.login(userName, password.text, sessionIndex)
    }

    // Pin the XFCE X11 session regardless of what was used last time.
    Repeater {
        model: sessionModel
        delegate: Item {
            required property int index
            required property string file
            Component.onCompleted: if (file === "xfce.desktop") root.sessionIndex = index
        }
    }

    Connections {
        target: sddm
        function onLoginFailed() {
            root.busy = false
            password.text = ""
            status.show("ACCESS DENIED — TRY AGAIN", "#ff6b81")
            shake.restart()
            password.forceActiveFocus()
        }
        function onLoginSucceeded() {
            status.show("WELCOME", accent)
            outro.start()
        }
    }

    Rectangle { anchors.fill: parent; color: "#000308" }

    Image {
        anchors.fill: parent
        source: config.stringValue("background")
        fillMode: Image.PreserveAspectCrop
        smooth: true
        cache: false
    }

    // Breathing glow on the emblem core
    Canvas {
        id: core
        readonly property real r: 46 * root.sx
        x: config.realValue("emblemX") * root.sx - r
        y: config.realValue("emblemY") * root.sy - r
        width: r * 2
        height: r * 2
        onPaint: {
            const ctx = getContext("2d")
            const g = ctx.createRadialGradient(r, r, 0, r, r, r)
            g.addColorStop(0.0, "rgba(220,240,255,0.9)")
            g.addColorStop(0.3, "rgba(95,180,255,0.45)")
            g.addColorStop(1.0, "rgba(40,110,255,0.0)")
            ctx.fillStyle = g
            ctx.fillRect(0, 0, width, height)
        }
        opacity: 0
        SequentialAnimation on opacity {
            loops: Animation.Infinite
            PauseAnimation { duration: 900 }
            NumberAnimation { to: 0.55; duration: 1800; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.0; duration: 1800; easing.type: Easing.InOutSine }
        }
    }

    // Slow stardust drifting upward
    Repeater {
        model: 34
        delegate: Rectangle {
            id: mote
            required property int index
            readonly property real seed: Math.abs(Math.sin(index * 12.9898) * 43758.5453) % 1
            readonly property real seed2: Math.abs(Math.sin(index * 78.233) * 12345.678) % 1
            width: (1.4 + seed2 * 1.8) * root.sx
            height: width
            radius: width / 2
            color: "#cfe6ff"
            x: seed * root.width
            opacity: 0
            SequentialAnimation {
                running: true
                loops: Animation.Infinite
                PauseAnimation { duration: 600 + mote.seed2 * 6000 }
                ParallelAnimation {
                    NumberAnimation {
                        target: mote; property: "y"
                        from: root.height * (0.55 + mote.seed * 0.45); to: root.height * (0.05 + mote.seed2 * 0.3)
                        duration: 14000 + mote.seed * 9000
                    }
                    SequentialAnimation {
                        NumberAnimation { target: mote; property: "opacity"; to: 0.15 + mote.seed2 * 0.35; duration: 2500 }
                        PauseAnimation { duration: 9000 + mote.seed * 4000 }
                        NumberAnimation { target: mote; property: "opacity"; to: 0; duration: 2500 }
                    }
                }
            }
        }
    }

    // ---------------------------------------------------------------- login panel
    Item {
        id: panel
        width: 440 * root.sx
        height: 250 * root.sy
        x: (root.width - width) / 2
        y: config.intValue("panelTop") * root.sy + slide
        opacity: 0
        property real slide: 18 * root.sy
        property real shakeX: 0
        transform: Translate { x: panel.shakeX }

        ParallelAnimation {
            id: intro
            NumberAnimation { target: panel; property: "opacity"; to: 1; duration: 750; easing.type: Easing.OutCubic }
            NumberAnimation { target: panel; property: "slide"; to: 0; duration: 750; easing.type: Easing.OutCubic }
        }
        Timer { interval: 150; running: true; onTriggered: { intro.start(); password.forceActiveFocus() } }

        SequentialAnimation {
            id: shake
            loops: 1
            NumberAnimation { target: panel; property: "shakeX"; to: -14; duration: 50 }
            NumberAnimation { target: panel; property: "shakeX"; to: 12; duration: 70 }
            NumberAnimation { target: panel; property: "shakeX"; to: -8; duration: 70 }
            NumberAnimation { target: panel; property: "shakeX"; to: 4; duration: 60 }
            NumberAnimation { target: panel; property: "shakeX"; to: 0; duration: 50 }
        }

        Column {
            anchors.fill: parent
            spacing: 14 * root.sy

            Row {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 12 * root.sx
                Rectangle {
                    width: 34 * root.sx; height: width; radius: width / 2
                    color: "#0d2342"
                    border.color: root.accent; border.width: 1
                    Text {
                        anchors.centerIn: parent
                        text: root.userName.charAt(0).toUpperCase()
                        color: "white"
                        font.family: "Inter"; font.pixelSize: 16 * root.sx; font.weight: Font.DemiBold
                    }
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.userName.toUpperCase()
                    color: "#e6f0ff"
                    font.family: "Inter"; font.pixelSize: 18 * root.sx; font.letterSpacing: 5 * root.sx
                }
            }

            TextField {
                id: password
                width: parent.width
                height: 50 * root.sy
                echoMode: TextInput.Password
                passwordCharacter: "●"
                placeholderText: "PASSWORD"
                placeholderTextColor: "#5c6f8a"
                color: "white"
                enabled: !root.busy
                focus: true
                horizontalAlignment: TextInput.AlignHCenter
                font.family: "Inter"; font.pixelSize: 17 * root.sx; font.letterSpacing: 3 * root.sx
                selectByMouse: false
                background: Rectangle {
                    color: "#c0061224"
                    radius: 3
                    border.width: password.activeFocus ? 1.5 : 1
                    border.color: password.activeFocus ? root.accent : "#2a4466"
                    Behavior on border.color { ColorAnimation { duration: 200 } }
                }
                onAccepted: root.doLogin()
                onTextEdited: if (!root.busy) status.show(keyboard.capsLock ? "CAPS LOCK IS ON" : "", root.dim)
            }

            Button {
                id: loginButton
                width: parent.width
                height: 46 * root.sy
                enabled: !root.busy
                onClicked: root.doLogin()
                contentItem: Text {
                    text: "L O G I N"
                    color: "white"
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: "Inter"; font.pixelSize: 15 * root.sx; font.weight: Font.DemiBold
                }
                background: Rectangle {
                    radius: 3
                    opacity: loginButton.enabled ? 1 : 0.5
                    gradient: Gradient {
                        GradientStop { position: 0; color: loginButton.down ? "#1d4f8f" : (loginButton.hovered ? "#3a86e0" : "#2b6cc0") }
                        GradientStop { position: 1; color: loginButton.down ? "#123563" : (loginButton.hovered ? "#1f5ba8" : "#174a8c") }
                    }
                    border.color: "#7cc2ff"; border.width: 1
                }
            }

            Text {
                id: status
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                text: keyboard.capsLock ? "CAPS LOCK IS ON" : "ENTER PASSWORD TO CONTINUE"
                color: root.dim
                font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 12 * root.sx; font.letterSpacing: 2 * root.sx
                function show(msg, col) { if (msg !== "") text = msg; color = col }
            }
        }
    }

    // ---------------------------------------------------------------- power
    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 1000 * root.sy
        spacing: 48 * root.sx
        opacity: panel.opacity * 0.85
        Repeater {
            model: [
                { label: "RESTART", can: sddm.canReboot, act: function() { sddm.reboot() } },
                { label: "SHUT DOWN", can: sddm.canPowerOff, act: function() { sddm.powerOff() } }
            ]
            delegate: Text {
                required property var modelData
                visible: modelData.can
                text: modelData.label
                color: hover.hovered ? "white" : root.dim
                font.family: "JetBrainsMono Nerd Font"; font.pixelSize: 12 * root.sx; font.letterSpacing: 3 * root.sx
                HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: modelData.act() }
            }
        }
    }

    // Seamless outro on login success: fade out login panel without black flash
    ParallelAnimation {
        id: outro
        running: false
        NumberAnimation { target: panel; property: "opacity"; to: 0; duration: 320; easing.type: Easing.OutQuad }
        NumberAnimation { target: panel; property: "slide"; to: 20 * root.sy; duration: 320; easing.type: Easing.InQuad }
    }
}
