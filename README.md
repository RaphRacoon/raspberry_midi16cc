# Granular Noise — Raspberry Pi Zero + RaspiAudio MIC+

Synthétiseur granulaire noise contrôlé par 16 CC MIDI (CC25-CC40).  
4 voix granulaires simultanées, buffer audio 2 secondes (micro live ou sample).

## Hardware

| Composant | Détail |
|---|---|
| **Cerveau** | Raspberry Pi Zero v1 |
| **Audio** | RaspiAudio MIC+ (I2S, sortie casque + micro intégré) |
| **MIDI** | Contrôleur USB 16 CC (via OTG + hub USB) |

### Connexion MIDI

Le Pi Zero a un seul port micro-USB OTG. Pour brancher un contrôleur MIDI USB :
```
[Pi Zero micro-USB] → [OTG adapter] → [USB Hub] → [Contrôleur MIDI]
                                                  → [Alimentation]
```
Un hub USB avec alimentation propre est nécessaire pour éviter les chutes de tension.

## Mapping CC MIDI

| CC | Paramètre | Plage | Description |
|---|---|---|---|
| **CC25** | Grain Size | 10 – 500 ms | Durée de chaque grain |
| **CC26** | Grain Density | 1 – 100 /sec | Nombre de grains par seconde |
| **CC27** | Read Position | 0 – 100% | Point de lecture dans le buffer |
| **CC28** | Position Scatter | 0 – 100% | Dispersion aléatoire de la position |
| **CC29** | Pitch Ratio | 0.25x – 4x | Transposition du grain |
| **CC30** | Pitch Random | 0 – 100% | Aléatoire de hauteur |
| **CC31** | Envelope Shape | — | Forme de l'enveloppe grain |
| **CC32** | Pan Spread | 0 – 100% | Largeur stéréo |
| **CC33** | Reverb Amount | 0 – 100% | Quantité de réverbération |
| **CC34** | Filter Freq | 80 – 18080 Hz | Fréquence du filtre |
| **CC35** | Filter Res | 0 – 0.99 | Résonance du filtre |
| **CC36** | Freeze | off / on | Geler le buffer (plus d'enregistrement) |
| **CC37** | Record | off / on | Enregistrer le micro dans le buffer |
| **CC38** | Distortion | 1x – 21x | Saturation waveshaper (tanh) |
| **CC39** | Master Volume | 0 – 100% | Volume de sortie général |
| **CC40** | Dry/Wet | — | Mix signal sec/granularisé |

## Installation

### 1. Prérequis OS

```bash
# Raspberry Pi OS Lite (32-bit) recommandé pour Pi Zero
# Flash avec Raspberry Pi Imager, activer SSH dans les options avancées
```

### 2. Config RaspiAudio MIC+

```bash
# Suivre le guide officiel RaspiAudio pour activer le HAT
# Le overlay dtoverlay=googlevoicehat-soundcard doit etre dans /boot/config.txt
```

### 3. Cloner et installer

```bash
git clone https://github.com/raphracoon/raspberry_midi16cc.git
cd raspberry_midi16cc
chmod +x scripts/*.sh
sudo ./scripts/setup.sh
sudo reboot
```

### 4. Lancer

```bash
./scripts/start.sh
# ou en service automatique au boot :
sudo systemctl start granular
```

## Architecture logicielle

```
MIDI CC25-40
    |
    v
[ctlin] -> [MIDI-INPUT] -> send~ vers parametres
                               |
                     +---------+---------+
                     v         v         v
               [BUFFER]  [SCHEDULER]  [VOICES x4]
               (table     (metro +      (phasor~ +
               88200)      triggers)    tabread4~)
                                            |
                                       [MIXER-FX]
                                       filtre vcf~
                                       distort tanh~
                                       volume line~
                                            |
                                         [dac~]
```

## Optimisations Pi Zero

Le Pi Zero v1 (ARM11, 1GHz, 512MB) est limité. Reglages start.sh :
- **Sample rate** : 44100 Hz
- **Buffer JACK** : 1024 frames (~23ms latence) — stable sur Zero
- **Voix simultanées** : 4 maximum

## Fichiers

```
pd/
  granular.pd       — patch principal Pure Data
config/
  asound.conf       — config ALSA
  granular.service  — service systemd
scripts/
  setup.sh          — installation automatique
  start.sh          — demarrage JACK + PD
```
