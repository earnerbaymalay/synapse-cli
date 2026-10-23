#!/usr/bin/env bash
# ==============================================================================
# font-tune.sh: Dynamic Font & Spacing Manager for Kitty, XFCE & GTK
# ==============================================================================
set -euo pipefail

KITTY_CONF="$HOME/.config/kitty/kitty.conf"
TERMINALRC="$HOME/.config/xfce4/terminal/terminalrc"
GTK3_CONF="$HOME/.config/gtk-3.0/settings.ini"

usage() {
    echo "Usage: font-tune [status | preset | spacing | reload]"
    echo ""
    echo "Commands:"
    echo "  status                  Show active font and spacing configuration"
    echo "  preset <name> [size]    Apply a typography preset:"
    echo "                            noto       - Noto Sans UI + Source Code Pro monospace (balanced, comfortable)"
    echo "                            jetbrains  - Inter UI + JetBrainsMono Nerd Font Mono (modern coding)"
    echo "                            sourcecode - Noto Sans UI + Source Code Pro (classic clean)"
    echo "                            inter      - Inter UI + Inter Bold title + JetBrainsMono Mono"
    echo "  spacing <col> <line>    Adjust Kitty cell spacing (-2 to +5, e.g. 'spacing 0 1')"
    echo "  reload                  Trigger live reload for Kitty, XFCE, and GTK"
    exit 1
}

apply_font() {
    local preset="${1:-}"
    local size="${2:-10}"

    case "$preset" in
        noto|clean)
            local ui_font="Noto Sans $size"
            local mono_font="Source Code Pro $size"
            local title_font="Noto Sans Bold $size"
            local kitty_family="Source Code Pro"
            ;;
        jetbrains|nerd)
            local ui_font="Noto Sans $size"
            local mono_font="JetBrainsMono Nerd Font Mono $size"
            local title_font="Noto Sans Bold $size"
            local kitty_family="JetBrainsMono Nerd Font Mono"
            ;;
        sourcecode|adobe)
            local ui_font="Noto Sans $size"
            local mono_font="Source Code Pro $size"
            local title_font="Noto Sans Bold $size"
            local kitty_family="Source Code Pro"
            ;;
        inter)
            local ui_font="Inter $size"
            local mono_font="JetBrainsMono Nerd Font Mono $size"
            local title_font="Inter Bold $size"
            local kitty_family="JetBrainsMono Nerd Font Mono"
            ;;
        *)
            echo "Unknown preset: $preset"
            usage
            ;;
    esac

    echo "Applying preset: $preset (UI: $ui_font, Mono: $mono_font)..."

    # 1. Update XFCE XSettings
    xfconf-query -c xsettings -p /Gtk/FontName -s "$ui_font" 2>/dev/null || true
    xfconf-query -c xsettings -p /Gtk/MonospaceFontName -s "$mono_font" 2>/dev/null || true
    xfconf-query -c xsettings -p /Xft/Antialias -s 1 2>/dev/null || true
    xfconf-query -c xsettings -p /Xft/Hinting -s 1 2>/dev/null || true
    xfconf-query -c xsettings -p /Xft/HintStyle -s "hintslight" 2>/dev/null || true
    xfconf-query -c xsettings -p /Xft/RGBA -s "rgb" 2>/dev/null || true

    # 2. Update XFWM4 Window Title
    xfconf-query -c xfwm4 -p /general/title_font -s "$title_font" 2>/dev/null || true

    # 3. Update GTK 3 settings.ini
    if [ -f "$GTK3_CONF" ]; then
        sed -i "s/^gtk-font-name=.*/gtk-font-name=$ui_font/" "$GTK3_CONF" 2>/dev/null || true
        sed -i 's/^gtk-xft-hintstyle=.*/gtk-xft-hintstyle=hintslight/' "$GTK3_CONF" 2>/dev/null || true
        sed -i 's/^gtk-xft-rgba=.*/gtk-xft-rgba=rgb/' "$GTK3_CONF" 2>/dev/null || true
    fi

    # 4. Update XFCE Terminal
    if [ -f "$TERMINALRC" ]; then
        sed -i "s/^FontName=.*/FontName=$mono_font/" "$TERMINALRC" 2>/dev/null || true
    fi

    # 5. Update Kitty config
    mkdir -p "$(dirname "$KITTY_CONF")"
    if grep -q "^font_family" "$KITTY_CONF" 2>/dev/null; then
        sed -i "s/^font_family .*/font_family      $kitty_family/" "$KITTY_CONF"
        sed -i "s/^font_size .*/font_size        $size/" "$KITTY_CONF"
    else
        cat <<EOF >> "$KITTY_CONF"

# Font configuration
font_family      $kitty_family
bold_font        auto
italic_font      auto
bold_italic_font auto
font_size        $size
adjust_line_height  0
adjust_column_width 0
EOF
    fi

    # 6. Live reload
    reload
    echo "Preset '$preset' applied successfully!"
}

set_spacing() {
    local col="${1:-0}"
    local line="${2:-0}"

    echo "Setting Kitty column spacing: $col, line spacing: $line..."
    if grep -q "^adjust_column_width" "$KITTY_CONF" 2>/dev/null; then
        sed -i "s/^adjust_column_width .*/adjust_column_width $col/" "$KITTY_CONF"
        sed -i "s/^adjust_line_height .*/adjust_line_height  $line/" "$KITTY_CONF"
    else
        echo "adjust_column_width $col" >> "$KITTY_CONF"
        echo "adjust_line_height  $line" >> "$KITTY_CONF"
    fi

    pkill -USR1 -u "$USER" kitty 2>/dev/null || true
    echo "Spacing updated."
}

reload() {
    pkill -USR1 -u "$USER" kitty 2>/dev/null || true
}

show_status() {
    echo "=== Current Font & Spacing Status ==="
    echo "GTK UI Font:        $(xfconf-query -c xsettings -p /Gtk/FontName 2>/dev/null || echo 'N/A')"
    echo "GTK Monospace:      $(xfconf-query -c xsettings -p /Gtk/MonospaceFontName 2>/dev/null || echo 'N/A')"
    echo "Window Title Font:  $(xfconf-query -c xfwm4 -p /general/title_font 2>/dev/null || echo 'N/A')"
    echo "Hinting Style:      $(xfconf-query -c xsettings -p /Xft/HintStyle 2>/dev/null || echo 'N/A')"
    echo "Subpixel RGBA:      $(xfconf-query -c xsettings -p /Xft/RGBA 2>/dev/null || echo 'N/A')"
    echo "XFCE Terminal Font: $(grep '^FontName=' "$TERMINALRC" 2>/dev/null || echo 'N/A')"
    echo "Kitty Font:         $(grep '^font_family' "$KITTY_CONF" 2>/dev/null || echo 'Default monospace')"
    echo "Kitty Spacing:      $(grep '^adjust_' "$KITTY_CONF" 2>/dev/null | tr '\n' ' ' || echo 'Default')"
}

case "${1:-}" in
    status)
        show_status
        ;;
    preset)
        apply_font "${2:-}" "${3:-10}"
        ;;
    spacing)
        set_spacing "${2:-0}" "${3:-0}"
        ;;
    reload)
        reload
        ;;
    *)
        usage
        ;;
esac
