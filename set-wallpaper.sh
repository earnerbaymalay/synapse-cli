#!/usr/bin/env bash
# ==============================================================================
# set-wallpaper.sh: System Wallpaper Switcher & Workspace Randomizer
# ==============================================================================
set -euo pipefail

WALLPAPER_DIR="/usr/share/backgrounds/wallpapers"

usage() {
    echo "Usage: set-wallpaper [random | cycle | list | <wallpaper_name>]"
    echo ""
    echo "Commands:"
    echo "  random    - Sets a random distinct wallpaper on workspaces 0-3"
    echo "  cycle     - Force a cycle rotation across all workspaces"
    echo "  list      - List all wallpapers in $WALLPAPER_DIR"
    echo "  <name>    - Set a specific wallpaper across all workspaces"
    exit 1
}

apply_all() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "Error: Wallpaper not found at $file" >&2
        exit 1
    fi

    for prop in $(xfconf-query -c xfce4-desktop -lv 2>/dev/null | grep 'last-image' | awk '{print $1}'); do
        xfconf-query -c xfce4-desktop -p "$prop" -s "$file" 2>/dev/null || true
    done
    xfdesktop --reload
    echo "Wallpaper successfully set to: $(basename "$file")"
}

case "${1:-}" in
    random|rand)
        shopt -s nullglob
        files=("$WALLPAPER_DIR"/*.{jpg,png,svg})
        if [ ${#files[@]} -lt 4 ]; then
            echo "Not enough wallpapers found in $WALLPAPER_DIR"
            exit 1
        fi
        # Pick 4 random distinct files
        mapfile -t selected < <(printf "%s\n" "${files[@]}" | shuf -n 4)
        for i in {0..3}; do
            xfconf-query -c xfce4-desktop -p "/backdrop/screen0/monitoreDP-1/workspace$i/last-image" -s "${selected[$i]}" 2>/dev/null || true
            echo "Workspace $i -> $(basename "${selected[$i]}")"
        done
        xfdesktop --reload
        echo "✔ Randomized wallpapers across all 4 workspaces."
        ;;
    cycle)
        xfdesktop --reload
        echo "✔ Triggered xfdesktop wallpaper cycle."
        ;;
    list|ls)
        echo "Installed wallpapers in $WALLPAPER_DIR:"
        ls -1 "$WALLPAPER_DIR"
        ;;
    "")
        usage
        ;;
    *)
        # Try matching filename
        match=$(find "$WALLPAPER_DIR" -maxdepth 1 -iname "*$1*" | head -n 1)
        if [ -n "$match" ] && [ -f "$match" ]; then
            apply_all "$match"
        else
            echo "Error: No matching wallpaper for '$1' in $WALLPAPER_DIR"
            exit 1
        fi
        ;;
esac
