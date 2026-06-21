#!/bin/bash
# Setup complet pour granular noise - Pi Zero + RaspiAudio MIC+
set -e

echo "=== Setup Granular Noise Pi Zero ==="

# Mise à jour système
sudo apt-get update -y
sudo apt-get upgrade -y

# Pure Data headless + externals nécessaires
sudo apt-get install -y \
    puredata \
    pd-zexy \
    pd-chaos \
    pd-iemlib \
    jackd2 \
    a2jmidid \
    alsa-utils \
    libasound2-dev

# Config ALSA pour RaspiAudio MIC+
sudo cp "$(dirname "$0")/../config/asound.conf" /etc/asound.conf

# Config RaspiAudio MIC+ dans /boot/config.txt
BOOT_CONFIG="/boot/config.txt"
if ! grep -q "raspiaudio" "$BOOT_CONFIG" 2>/dev/null; then
    echo "" | sudo tee -a "$BOOT_CONFIG"
    echo "# RaspiAudio MIC+" | sudo tee -a "$BOOT_CONFIG"
    echo "dtparam=i2s=on" | sudo tee -a "$BOOT_CONFIG"
    echo "dtoverlay=googlevoicehat-soundcard" | sudo tee -a "$BOOT_CONFIG"
    echo "  --> /boot/config.txt mis à jour, redémarrage nécessaire"
fi

# Désactiver audio HDMI pour libérer ressources
if ! grep -q "dtparam=audio=off" "$BOOT_CONFIG" 2>/dev/null; then
    echo "dtparam=audio=off" | sudo tee -a "$BOOT_CONFIG"
fi

# Config JACK realtime sans root
sudo usermod -a -G audio "$USER"
if ! grep -q "@audio" /etc/security/limits.conf; then
    echo "@audio   -  rtprio     95" | sudo tee -a /etc/security/limits.conf
    echo "@audio   -  memlock    unlimited" | sudo tee -a /etc/security/limits.conf
fi

# Optimisations Pi Zero pour temps réel
sudo sed -i 's/^#kernel.sched_rt_runtime_us.*/kernel.sched_rt_runtime_us = -1/' /etc/sysctl.conf
echo "kernel.sched_rt_runtime_us = -1" | sudo tee -a /etc/sysctl.conf

# Installer le service de démarrage automatique
sudo cp "$(dirname "$0")/../config/granular.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable granular.service

echo ""
echo "=== Setup terminé ==="
echo "  Redémarre la Pi pour appliquer la config audio."
echo "  Ensuite: sudo systemctl start granular"
