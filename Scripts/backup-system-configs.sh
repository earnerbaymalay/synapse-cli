#!/usr/bin/env bash
# ==============================================================================
# System Configuration & Dotfiles Backup Utility
# Backs up custom XFCE launcher configs, xcape bindings, Hatter icons,
# Catppuccin themes, and terminal configs for Dell Latitude 7490 (EndeavourOS).
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-$HOME/Backups/system-configs}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_NAME="system-configs-backup-${TIMESTAMP}.tar.gz"
TARGET_ARCHIVE="${BACKUP_DIR}/${ARCHIVE_NAME}"
MANIFEST_FILE="${BACKUP_DIR}/manifest-${TIMESTAMP}.txt"

mkdir -p "${BACKUP_DIR}"

log() {
    printf "\033[1;34m[INFO]\033[0m %s\n" "$1"
}

success() {
    printf "\033[1;32m[SUCCESS]\033[0m %s\n" "$1"
}

warn() {
    printf "\033[1;33m[WARN]\033[0m %s\n" "$1"
}

error() {
    printf "\033[1;31m[ERROR]\033[0m %s\n" "$1" >&2
}

# Collect list of existing items to back up
ITEMS_TO_BACKUP=()

add_if_exists() {
    local target="$1"
    if [ -e "$target" ]; then
        ITEMS_TO_BACKUP+=("$target")
    else
        warn "Path not found (skipping): $target"
    fi
}

log "Scanning system configurations and dotfiles..."

# 1. XFCE Configurations
add_if_exists "$HOME/.config/xfce4/xfconf/xfce-perchannel-xml"
add_if_exists "$HOME/.config/xfce4/panel"

# 2. Launcher & Autostart bindings (xcape, custom desktop entries)
add_if_exists "$HOME/.config/autostart/xcape.desktop"
if [ -f "/usr/local/bin/xfce-launcher-toggle" ]; then
    add_if_exists "/usr/local/bin/xfce-launcher-toggle"
fi

# 3. Themes & Icons
for icon_dir in "$HOME/.local/share/icons"/Hatter*; do
    if [ -d "$icon_dir" ]; then
        add_if_exists "$icon_dir"
    fi
done

for theme_dir in "$HOME/.themes"/Catppuccin*; do
    if [ -d "$theme_dir" ]; then
        add_if_exists "$theme_dir"
    fi
done

# 4. Terminal & Shell Productivity Configs
add_if_exists "$HOME/.config/kitty/kitty.conf"
add_if_exists "$HOME/.config/starship.toml"
add_if_exists "$HOME/.bashrc"

if [ ${#ITEMS_TO_BACKUP[@]} -eq 0 ]; then
    error "No configuration items found to back up."
    exit 1
fi

log "Creating backup archive: ${TARGET_ARCHIVE}"
tar -czpf "${TARGET_ARCHIVE}" "${ITEMS_TO_BACKUP[@]}" 2>/dev/null

# Generate manifest and checksums
log "Generating backup manifest and SHA256 checksum..."
sha256sum "${TARGET_ARCHIVE}" > "${TARGET_ARCHIVE}.sha256"

{
    echo "Backup Created: $(date)"
    echo "Archive: ${ARCHIVE_NAME}"
    echo "SHA256: $(cat "${TARGET_ARCHIVE}.sha256" | cut -d' ' -f1)"
    echo ""
    echo "Included Files & Directories:"
    for item in "${ITEMS_TO_BACKUP[@]}"; do
        echo " - $item"
    done
} > "${MANIFEST_FILE}"

# Keep only the last 5 backups to prevent disk bloat
log "Pruning old backups (retaining newest 5)..."
find "${BACKUP_DIR}" -name "system-configs-backup-*.tar.gz*" -type f -printf '%T+ %p\n' | \
    sort -r | tail -n +11 | cut -d' ' -f2- | xargs -r rm -f

BACKUP_SIZE=$(du -h "${TARGET_ARCHIVE}" | cut -f1)
success "Backup completed successfully!"
printf "  -> Archive:  %s (%s)\n" "${TARGET_ARCHIVE}" "${BACKUP_SIZE}"
printf "  -> Manifest: %s\n" "${MANIFEST_FILE}"
printf "  -> Checksum: %s\n" "${TARGET_ARCHIVE}.sha256"
