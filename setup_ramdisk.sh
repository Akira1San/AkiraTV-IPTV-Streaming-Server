#!/bin/bash
# AkiraTV Linux RAM Disk Setup Script
# Creates a tmpfs RAM disk equivalent to Windows ImDisk for R:/akiratv
# Usage: ./setup_ramdisk.sh [size] [mount|unmount|status|persistent]

set -e

# Configuration
MOUNT_POINT="/home/akira/akiratv"
DEFAULT_SIZE="512M"

# Function to print usage (defined early so it can be called for help)
usage() {
    echo "AkiraTV Linux RAM Disk Setup Script"
    echo ""
    echo "Usage: $0 [size] [command]"
    echo ""
    echo "Arguments:"
    echo "  size         RAM disk size (default: 512M). Examples: 512M, 1G, 2G"
    echo ""
    echo "Commands:"
    echo "  mount        Mount the RAM disk (default)"
    echo "  unmount      Unmount the RAM disk"
    echo "  status       Show RAM disk status"
    echo "  persistent  Add to /etc/fstab for auto-mount on reboot"
    echo "  remove       Remove from /etc/fstab"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Mount with default size (512M)"
    echo "  $0 1G                 # Mount with 1GB size"
    echo "  $0 512M mount         # Mount with specific size"
    echo "  $0 1G persistent      # Add 1GB RAM disk to fstab"
    echo "  $0 status             # Check if mounted"
    echo "  $0 unmount            # Unmount RAM disk"
    echo ""
    echo "Note: RAM disk contents are lost on reboot unless persistent option is used"
}

# Parse arguments - check for help first
if [[ "$1" == "help" || "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
fi

# Determine action and size
if [[ "$1" == "mount" || "$1" == "unmount" || "$1" == "status" || "$1" == "persistent" || "$1" == "remove" ]]; then
    ACTION="$1"
    SIZE="$DEFAULT_SIZE"
elif [[ "$2" == "mount" || "$2" == "unmount" || "$2" == "status" || "$2" == "persistent" || "$2" == "remove" ]]; then
    SIZE="${1:-$DEFAULT_SIZE}"
    ACTION="$2"
else
    SIZE="${1:-$DEFAULT_SIZE}"
    ACTION="mount"
fi

# Validate SIZE format (e.g., 512M, 1G)
if [[ ! "$SIZE" =~ ^[0-9]+[KMG]?$ ]]; then
    log_error "Invalid size format: '$SIZE'. Use numbers with optional K/M/G suffix (e.g., 512M, 1G)"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_warn "Not running as root. Some operations may require sudo."
        return 1
    fi
    return 0
}

# Create mount point
create_mount_point() {
     log_info "Creating mount point: $MOUNT_POINT"
     mkdir -p "$MOUNT_POINT"
     chmod 755 "$MOUNT_POINT"
     log_info "Mount point created successfully"
}

# Mount tmpfs
do_mount() {
    # Check if already mounted
    if mountpoint -q "$MOUNT_POINT"; then
        log_info "RAM disk is already mounted at $MOUNT_POINT"
        show_status
        return 0
    fi
    
    create_mount_point
    
    log_info "Mounting tmpfs at $MOUNT_POINT with size $SIZE..."
    mount -t tmpfs -o size=$SIZE tmpfs "$MOUNT_POINT"
    
    if mountpoint -q "$MOUNT_POINT"; then
        log_info "RAM disk mounted successfully!"
        show_status
    else
        log_error "Failed to mount RAM disk"
        exit 1
    fi
}

# Unmount tmpfs
do_unmount() {
    if ! mountpoint -q "$MOUNT_POINT"; then
        log_info "RAM disk is not mounted at $MOUNT_POINT"
        return 0
    fi
    
    log_warn "Unmounting RAM disk. All data will be lost!"
    log_info "Make sure AkiraTV is not running..."
    
    umount "$MOUNT_POINT"
    
    if ! mountpoint -q "$MOUNT_POINT"; then
        log_info "RAM disk unmounted successfully"
    else
        log_error "Failed to unmount RAM disk"
        exit 1
    fi
}

# Show status
show_status() {
    echo ""
    echo "=== RAM Disk Status ==="
    echo "Mount point: $MOUNT_POINT"
    
    if mountpoint -q "$MOUNT_POINT"; then
        echo "Status: MOUNTED"
        df -h "$MOUNT_POINT" | tail -1
    else
        echo "Status: NOT MOUNTED"
    fi
    echo "========================"
}

# Add to fstab for persistent mount
do_persistent() {
    check_root || exit 1
    
    FSTAB_ENTRY="tmpfs $MOUNT_POINT tmpfs defaults,size=$SIZE 0 0"
    
    # Check if entry already exists
    if grep -qF "$MOUNT_POINT" /etc/fstab; then
        log_warn "Entry already exists in /etc/fstab"
        log_info "Current entry:"
        grep "$MOUNT_POINT" /etc/fstab
        return 0
    fi
    
    log_info "Adding entry to /etc/fstab..."
    echo "$FSTAB_ENTRY" >> /etc/fstab
    log_info "Entry added successfully"
    log_info "The RAM disk will now mount automatically on reboot"
    log_info ""
    log_info "To apply without rebooting, run: mount $MOUNT_POINT"
}

# Remove from fstab
do_remove_persistent() {
    check_root || exit 1
    
    if ! grep -qF "$MOUNT_POINT" /etc/fstab; then
        log_info "No entry found in /etc/fstab"
        return 0
    fi
    
    log_info "Removing entry from /etc/fstab..."
    grep -vF "$MOUNT_POINT" /etc/fstab > /etc/fstab.tmp && mv /etc/fstab.tmp /etc/fstab
    log_info "Entry removed successfully"
}

# Main
case "$ACTION" in
    mount)
        do_mount
        ;;
    unmount)
        check_root
        do_unmount
        ;;
    status)
        show_status
        ;;
    persistent)
        do_persistent
        ;;
    remove)
        do_remove_persistent
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        log_error "Unknown command: $ACTION"
        usage
        exit 1
        ;;
esac