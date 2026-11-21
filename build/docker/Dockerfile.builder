# Kill-Day OS builder: everything needed to produce the ISO, branding and portal.
FROM --platform=linux/amd64 debian:trixie
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    live-build debootstrap squashfs-tools xorriso mtools dosfstools parted gdisk \
    cryptsetup-bin exfatprogs e2fsprogs rsync curl wget ca-certificates xz-utils zstd \
    grub-pc-bin grub-efi-amd64-bin grub-common grub2-common shim-signed grub-efi-amd64-signed \
    syslinux-common isolinux memtest86+ \
    librsvg2-bin python3 python3-pil python3-reportlab shellcheck jq poppler-utils \
    golang-go nodejs npm fontconfig file udev kmod util-linux procps
WORKDIR /work
