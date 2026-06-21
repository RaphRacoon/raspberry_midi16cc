#!/bin/bash
# Démarrage JACK + MIDI bridge + Pure Data granulaire
# Pour Pi Zero + RaspiAudio MIC+

PATCH_DIR="$(dirname "$0")/../pd"
PATCH="$PATCH_DIR/granular.pd"

# Paramètres JACK optimisés Pi Zero (latence ~23ms, stable)
JACK_RATE=44100
JACK_PERIOD=1024
JACK_NPERIODS=2

# Détecter automatiquement la carte audio (prend la première carte non HDMI)
JACK_DEVICE=$(aplay -l 2>/dev/null | grep "^card" | grep -v "HDMI\|hdmi" | head -1 | awk '{gsub(/[,:]/, "", $2); print "hw:"$2}')
JACK_DEVICE="${JACK_DEVICE:-hw:0}"

echo "=== Démarrage Granular Noise ==="
echo "  Audio: $JACK_DEVICE @ ${JACK_RATE}Hz, période ${JACK_PERIOD}"

# Requis en mode headless (pas de dbus/X11)
export JACK_NO_AUDIO_RESERVATION=1

# Tuer les instances existantes
pkill jackd 2>/dev/null || true
pkill a2jmidid 2>/dev/null || true
pkill pd 2>/dev/null || true
sleep 1

# Démarrer JACK
jackd -R -d alsa \
    -d "$JACK_DEVICE" \
    -r "$JACK_RATE" \
    -p "$JACK_PERIOD" \
    -n "$JACK_NPERIODS" \
    -s \
    &
JACK_PID=$!

sleep 2

# Vérifier que JACK tourne
if ! jack_lsp > /dev/null 2>&1; then
    echo "ERREUR: JACK n'a pas démarré. Vérifie la config audio."
    exit 1
fi

# Bridge MIDI USB → JACK
a2jmidid -e &
A2J_PID=$!

sleep 1

echo "  MIDI bridge démarré"
echo "  Ports MIDI disponibles:"
aconnect -l 2>/dev/null | grep -v "^$" | head -20

# Démarrer Pure Data en mode headless
pd -nogui \
   -jack \
   -alsamidi \
   -rt \
   -audiobuf 50 \
   -open "$PATCH" \
   &
PD_PID=$!

echo ""
echo "=== Granular Noise actif ==="
echo "  PD PID: $PD_PID"
echo "  JACK PID: $JACK_PID"
echo "  Ctrl+C pour arrêter"

# Connecter le contrôleur MIDI automatiquement
sleep 3
# Cherche un périphérique MIDI USB et connecte-le à PD
MIDI_CLIENT=$(aconnect -l 2>/dev/null | grep -i "midi\|controller\|usb" | head -1 | awk '{print $2}' | tr -d ':')
if [ -n "$MIDI_CLIENT" ]; then
    PD_CLIENT=$(aconnect -l 2>/dev/null | grep -i "pure\|pd" | head -1 | awk '{print $2}' | tr -d ':')
    if [ -n "$PD_CLIENT" ]; then
        aconnect "$MIDI_CLIENT" "$PD_CLIENT" 2>/dev/null && echo "  MIDI connecté: $MIDI_CLIENT → $PD_CLIENT"
    fi
fi

# Attendre Ctrl+C
trap "pkill -P $$ ; echo 'Arrêt.'" SIGINT SIGTERM
wait $PD_PID
