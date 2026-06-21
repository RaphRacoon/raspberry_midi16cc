#!/bin/bash
# Bootstrap granular noise - Pi Zero + RaspiAudio MIC+
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/raphracoon/raspberry_midi16cc/main/install.sh)

set -e

REPO="https://github.com/raphracoon/raspberry_midi16cc.git"
INSTALL_DIR="$HOME/raspberry_midi16cc"

echo ""
echo "========================================"
echo "  GRANULAR NOISE - Installation"
echo "  Pi Zero + RaspiAudio MIC+"
echo "========================================"
echo ""

# Vérifier qu'on est bien sur une Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "ATTENTION: Ce script est prévu pour Raspberry Pi."
    read -r -p "Continuer quand même ? [o/N] " confirm
    [[ "$confirm" =~ ^[oO]$ ]] || exit 1
fi

# Mise à jour système
echo "[1/6] Mise à jour du système..."
sudo apt-get update -y -q
sudo apt-get upgrade -y -q

# Dépendances
echo "[2/6] Installation des dépendances..."
sudo apt-get install -y -q \
    git \
    puredata \
    pd-zexy \
    pd-iemlib \
    jackd2 \
    a2jmidid \
    alsa-utils

# Cloner le dépôt
echo "[3/6] Clonage du dépôt..."
if [ -d "$INSTALL_DIR" ]; then
    echo "  Dossier existant, mise à jour..."
    git -C "$INSTALL_DIR" pull
else
    git clone "$REPO" "$INSTALL_DIR"
fi

# Config ALSA
echo "[4/6] Configuration audio (RaspiAudio MIC+)..."
sudo cp "$INSTALL_DIR/config/asound.conf" /etc/asound.conf

# Config /boot/config.txt pour RaspiAudio MIC+
BOOT_CONFIG="/boot/config.txt"
[ -f "/boot/firmware/config.txt" ] && BOOT_CONFIG="/boot/firmware/config.txt"

if ! grep -q "googlevoicehat-soundcard" "$BOOT_CONFIG" 2>/dev/null; then
    {
        echo ""
        echo "# RaspiAudio MIC+"
        echo "dtparam=i2s=on"
        echo "dtoverlay=googlevoicehat-soundcard"
        echo "dtparam=audio=off"
    } | sudo tee -a "$BOOT_CONFIG" > /dev/null
    echo "  /boot/config.txt mis à jour."
fi

# Permissions realtime audio
echo "[5/6] Configuration des permissions audio temps réel..."
sudo usermod -a -G audio "$USER"
if ! grep -q "@audio.*rtprio" /etc/security/limits.conf; then
    {
        echo "@audio   -  rtprio     95"
        echo "@audio   -  memlock    unlimited"
        echo "@audio   -  nice       -10"
    } | sudo tee -a /etc/security/limits.conf > /dev/null
fi

# Paramètre kernel realtime
if ! grep -q "sched_rt_runtime_us" /etc/sysctl.conf; then
    echo "kernel.sched_rt_runtime_us = -1" | sudo tee -a /etc/sysctl.conf > /dev/null
fi

# Service systemd
echo "[6/6] Installation du service de démarrage automatique..."
# Remplacer le chemin utilisateur dans le service
sed "s|/home/pi|$HOME|g" "$INSTALL_DIR/config/granular.service" \
    | sed "s|User=pi|User=$USER|g" \
    | sudo tee /etc/systemd/system/granular.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable granular.service

# Rendre les scripts exécutables
chmod +x "$INSTALL_DIR/scripts/"*.sh

echo ""
echo "========================================"
echo "  Installation terminée !"
echo ""
echo "  Dossier : $INSTALL_DIR"
echo ""
echo "  Prochaines étapes :"
echo "  1. Redémarre la Pi : sudo reboot"
echo "  2. Branche ton contrôleur MIDI (via hub USB OTG)"
echo "  3. Lance le synthé : $INSTALL_DIR/scripts/start.sh"
echo "     ou automatiquement au boot (service activé)"
echo ""
echo "  Mapping CC MIDI :"
echo "    CC25 Grain Size    CC26 Density    CC27 Position"
echo "    CC28 Scatter       CC29 Pitch      CC30 Pitch RND"
echo "    CC31 Envelope      CC32 Pan        CC33 Reverb"
echo "    CC34 Filter Freq   CC35 Filter Res CC36 Freeze"
echo "    CC37 Record Mic    CC38 Distortion CC39 Volume"
echo "    CC40 Dry/Wet"
echo "========================================"
echo ""
read -r -p "Redémarrer maintenant ? [o/N] " reboot_now
[[ "$reboot_now" =~ ^[oO]$ ]] && sudo reboot
