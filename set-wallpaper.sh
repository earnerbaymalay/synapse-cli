#!/usr/bin/env bash
# ==============================================================================
# set-wallpaper.sh: CachyOS Emerald/Teal 4K Wallpaper Switcher
# ==============================================================================
set -euo pipefail

WALLPAPER_DIR="$HOME/Pictures/Wallpapers"

usage() {
    echo "Usage: set-wallpaper [topography | depths | forest | greenspace | flow]"
    echo ""
    echo "Available 4K/5K Wallpapers matching your Terminal ASCII Banner:"
    echo "  1) topography  - Cachy Topography (Subtle dark carbon slate with emerald contour lines)"
    echo "  2) depths      - Cachy Depths 5K (Minimal oceanic deep emerald/cyan gradient)"
    echo "  3) forest      - CachyOS Dark Forest 4K (Moody atmospheric emerald trees)"
    echo "  4) greenspace  - CachyOS Green Space 4K (Deep space void with emerald nebula)"
    echo "  5) flow        - Emerald Flow (Fluid minimalist ribbons)"
    exit 1
}

apply() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "Error: Wallpaper not found at $file" >&2
        exit 1
    fi

    for prop in $(xfconf-query -c xfce4-desktop -lv 2>/dev/null | grep 'last-image' | awk '{print $1}'); do
        xfconf-query -c xfce4-desktop -p "$prop" -s "$file" 2>/dev/null || true
    done
    echo "Wallpaper successfully set to: $(basename "$file")"
}

case "${1:-}" in
    topography|topo|1)
        apply "$WALLPAPER_DIR/Cachy_Topography.jpg"
        ;;
    depths|5k|2)
        apply "$WALLPAPER_DIR/Cachy_Depths_5K.png"
        ;;
    forest|darkforest|3)
        apply "$WALLPAPER_DIR/CachyOS_Dark_Forest_4K.png"
        ;;
    greenspace|space|4)
        apply "$WALLPAPER_DIR/CachyOS_GreenSpace_4K.png"
        ;;
    flow|emerald|5)
        apply "$WALLPAPER_DIR/Emerald_Flow.png"
        ;;
    list|ls)
        echo "Installed wallpapers in $WALLPAPER_DIR:"
        ls -1 "$WALLPAPER_DIR" | grep -iE 'cachy|emerald'
        ;;
    *)
        usage
        ;;
esac
