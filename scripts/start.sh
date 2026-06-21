#!/bin/bash
# Démarrage JACK + MIDI bridge + Pure Data granulaire
# Pour Pi Zero + RaspiAudio MIC+

PATCH_DIR="$(dirname "$0")/../pd"
PATCH="$PATCH_DIR/granular.pd"

JACK_RATE=48000
JACK_PERIOD=4096
JACK_NPERIODS=2

# Détecter automatiquement la carte audio (prend la première carte non HDMI)
JACK_DEVICE=$(aplay -l 2>/dev/null | grep "^card" | grep -v "HDMI\|hdmi" | head -1 | awk '{gsub(/[,:]/, "", $2); print "hw:"$2}')
JACK_DEVICE="${JACK_DEVICE:-hw:0}"

echo "=== Démarrage Granular Noise ==="
echo "  Audio: $JACK_DEVICE @ ${JACK_RATE}Hz, période ${JACK_PERIOD}"

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

sleep 3

if ! jack_lsp > /dev/null 2>&1; then
    echo "ERREUR: JACK n'a pas démarré."
    exit 1
fi

echo "  Ports JACK disponibles:"
jack_lsp

# Bridge MIDI USB → JACK
a2jmidid -e &
sleep 1

echo "  Ports MIDI:"
aconnect -l 2>/dev/null | head -30

# Démarrer Pure Data en mode headless
pd -nogui \
   -jack \
   -alsamidi \
   -rt \
   -audiobuf 500 \
   -open "$PATCH" \
   &
PD_PID=$!

echo ""
echo "=== Granular Noise actif ==="
echo "  PD PID: $PD_PID | JACK PID: $JACK_PID"

# Attendre que PD soit prêt puis connecter ses ports aux sorties physiques
sleep 5
echo "  Connexion ports JACK..."
jack_connect "Pure Data:output0" "system:playback_1" 2>/dev/null \
    || jack_connect "pure_data:output0" "system:playback_1" 2>/dev/null \
    || true
jack_connect "Pure Data:output1" "system:playback_2" 2>/dev/null \
    || jack_connect "pure_data:output1" "system:playback_2" 2>/dev/null \
    || true

echo "  Connexions JACK actives:"
jack_lsp -c 2>/dev/null | grep -A1 "Pure\|pure_data\|system"

# Connecter contrôleur MIDI
MIDI_CLIENT=$(aconnect -l 2>/dev/null | grep -i "MIDI Controller" | head -1 | awk '{print $2}' | tr -d ':')
if [ -n "$MIDI_CLIENT" ]; then
    PD_CLIENT=$(aconnect -l 2>/dev/null | grep -i "pure\|pd" | grep -v "Through" | head -1 | awk '{print $2}' | tr -d ':')
    if [ -n "$PD_CLIENT" ]; then
        aconnect "$MIDI_CLIENT" "$PD_CLIENT" 2>/dev/null && echo "  MIDI connecté: $MIDI_CLIENT → $PD_CLIENT"
    fi
fi

echo "  Ctrl+C pour arrêter"
trap "pkill jackd; pkill a2jmidid; pkill pd; echo 'Arrêt.'" SIGINT SIGTERM
wait $PD_PID
