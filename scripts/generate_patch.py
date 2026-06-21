#!/usr/bin/env python3
"""Génère pd/granular.pd avec des indices d'objets corrects."""

import os

lines = []

def canvas(name, w=800, h=600, x=50, y=50, font=12):
    lines.append(f"#N canvas {x} {y} {w} {h} {name} {font};")

def end_canvas(x, y, name):
    lines.append(f"#X restore {x} {y} pd {name};")

class Patch:
    def __init__(self):
        self.objects = []
        self.connections = []

    def add(self, line):
        idx = len(self.objects)
        self.objects.append(line)
        return idx

    def connect(self, src, outlet, dst, inlet):
        self.connections.append(f"#X connect {src} {outlet} {dst} {inlet};")

    def render(self):
        return self.objects + self.connections


# ── MIDI-INPUT ──────────────────────────────────────────────────────────────
def midi_input():
    p = Patch()
    ctlin    = p.add("#X obj 10 30 ctlin;")
    route    = p.add("#X obj 10 60 route 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40;")
    sends = [
        "grain-size", "grain-density", "grain-pos", "grain-scatter",
        "grain-pitch", "grain-pitch-rnd", "grain-env", "grain-pan",
        "reverb-amt", "filter-freq", "filter-res",
        "freeze", "record-trig", "distort-amt", "master-vol", "dry-wet",
    ]
    s_objs = [p.add(f"#X obj {10 + i*60} 100 s {name};") for i, name in enumerate(sends)]
    p.connect(ctlin, 0, route, 0)
    for i, s in enumerate(s_objs):
        p.connect(route, i, s, 0)
    return p.render()


# ── BUFFER MANAGER ──────────────────────────────────────────────────────────
def buffer_manager():
    p = Patch()
    table    = p.add("#X obj 10 10 table grain-buf 88200;")
    r_rec    = p.add("#X obj 10 60 r record-trig;")
    scale    = p.add("#X obj 10 90 * 0.007874;")
    gt       = p.add("#X obj 10 120 > 63;")
    sel      = p.add("#X obj 10 150 sel 1;")
    metro    = p.add("#X obj 10 180 metro 30;")
    f_idx    = p.add("#X obj 10 210 f 0;")
    plus1    = p.add("#X obj 10 240 + 1;")
    mod      = p.add("#X obj 10 270 mod 88200;")
    adc      = p.add("#X obj 10 310 adc~;")
    tw       = p.add("#X obj 10 340 tabwrite~ grain-buf;")
    r_freeze = p.add("#X obj 10 400 r freeze;")
    sf       = p.add("#X obj 10 430 * 0.007874;")
    gf       = p.add("#X obj 10 460 > 63;")
    sef      = p.add("#X obj 10 490 sel 1;")
    stop     = p.add("#X msg 10 520 stop;")

    p.connect(r_rec, 0, scale, 0)
    p.connect(scale, 0, gt, 0)
    p.connect(gt, 0, sel, 0)
    p.connect(sel, 0, metro, 0)
    p.connect(metro, 0, f_idx, 0)
    p.connect(f_idx, 0, plus1, 0)
    p.connect(plus1, 0, mod, 0)
    p.connect(mod, 0, f_idx, 1)
    p.connect(mod, 0, tw, 1)
    p.connect(adc, 0, tw, 0)
    p.connect(r_freeze, 0, sf, 0)
    p.connect(sf, 0, gf, 0)
    p.connect(gf, 0, sef, 0)
    p.connect(sef, 0, stop, 0)
    p.connect(stop, 0, metro, 0)
    return p.render()


# ── SCHEDULER ───────────────────────────────────────────────────────────────
def scheduler():
    p = Patch()
    r_den    = p.add("#X obj 10 10 r grain-density;")
    sc_den   = p.add("#X obj 10 40 * 0.007874;")
    expr_int = p.add("#X obj 10 70 expr max(10\\, 1000 / (($f1 * 100) + 1));")
    metro    = p.add("#X obj 10 100 metro 200;")
    trig4    = p.add("#X obj 10 130 t b b b b;")
    s1 = p.add("#X obj 10 170 s trig-1;")
    s2 = p.add("#X obj 90 170 s trig-2;")
    s3 = p.add("#X obj 170 170 s trig-3;")
    s4 = p.add("#X obj 250 170 s trig-4;")

    # scaled params sent to all voices via named sends
    params = [
        ("grain-pos",       "pos-n",       "* 0.007874"),
        ("grain-scatter",   "scatter-n",   "* 0.007874"),
        ("grain-size",      "size-ms",     "expr max(10\\, $f1 * 0.007874 * 490 + 10)"),
        ("grain-pitch",     "pitch-ratio", "expr $f1 * 0.007874 * 3.75 + 0.25"),
        ("grain-pan",       "pan-spread-n","* 0.007874"),
    ]
    y = 220
    for r_name, s_name, expr in params:
        r   = p.add(f"#X obj 10 {y} r {r_name};")
        op  = p.add(f"#X obj 10 {y+30} {expr};")
        s   = p.add(f"#X obj 10 {y+60} s {s_name};")
        p.connect(r, 0, op, 0)
        p.connect(op, 0, s, 0)
        y += 110

    p.connect(r_den, 0, sc_den, 0)
    p.connect(sc_den, 0, expr_int, 0)
    p.connect(expr_int, 0, metro, 0)
    p.connect(metro, 0, trig4, 0)
    p.connect(trig4, 0, s1, 0)
    p.connect(trig4, 1, s2, 0)
    p.connect(trig4, 2, s3, 0)
    p.connect(trig4, 3, s4, 0)
    return p.render()


# ── GRAIN VOICE ─────────────────────────────────────────────────────────────
def voice(n):
    p = Patch()
    r_trig  = p.add(f"#X obj 10 10 r trig-{n};")
    r_pos   = p.add("#X obj 10 40 r pos-n;")
    r_scat  = p.add("#X obj 10 70 r scatter-n;")
    r_size  = p.add("#X obj 10 100 r size-ms;")
    r_pitch = p.add("#X obj 10 130 r pitch-ratio;")
    r_pan   = p.add("#X obj 10 160 r pan-spread-n;")

    # position = pos + random scatter
    rnd_pos  = p.add("#X obj 200 70 random 1000;")
    sc_rnd   = p.add("#X obj 200 100 * 0.002;")
    off_rnd  = p.add("#X obj 200 130 - 1;")
    mul_sc   = p.add("#X obj 200 160 *;")           # scatter * random-1
    pos_sum  = p.add("#X obj 10 200 +;")            # pos + scatter
    clip_pos = p.add("#X obj 10 230 clip 0 1;")
    buf_pos  = p.add("#X obj 10 260 * 88199;")      # sample index start

    # phasor drives grain read
    phasor   = p.add("#X obj 10 300 phasor~;")      # inlet 0 = freq
    scale_ph = p.add("#X obj 10 330 * 88199;")      # phasor 0-1 → sample offset
    add_pos  = p.add("#X obj 10 360 +~ 0;")         # offset + start
    reader   = p.add("#X obj 10 390 tabread4~ grain-buf;")

    # envelope: hanning window via phasor
    env_ph   = p.add("#X obj 200 300 phasor~;")     # same freq
    pi_mul   = p.add("#X obj 200 330 * 3.14159;")
    sin_env  = p.add("#X obj 200 360 cos~;")        # cos(pi*phase) for hanning
    env_inv  = p.add("#X obj 200 390 *~ -0.5;")
    env_off  = p.add("#X obj 200 420 +~ 0.5;")

    apply_env = p.add("#X obj 10 430 *~;")

    # stereo pan
    rnd_pan  = p.add("#X obj 350 160 random 1000;")
    sc_pan   = p.add("#X obj 350 190 * 0.002;")
    off_pan  = p.add("#X obj 350 220 - 1;")
    mul_pan  = p.add("#X obj 350 250 *;")           # pan_spread * rnd
    pan_L    = p.add("#X obj 10 470 *~;")
    pan_R    = p.add("#X obj 200 470 *~;")
    inv_pan  = p.add("#X obj 200 500 *~ -1;")
    off_panR = p.add("#X obj 200 530 +~ 1;")

    sL = p.add(f"#X obj 10 560 s~ vout{n}-L;")
    sR = p.add(f"#X obj 200 560 s~ vout{n}-R;")

    # grain freq = 1/size_ms * 1000
    # size_ms comes as float from scheduler — convert to hz
    freq_obj = p.add("#X obj 10 295 expr 1000 / $f1;")  # size_ms → hz

    # Connections
    p.connect(r_trig, 0, rnd_pos, 0)
    p.connect(r_trig, 0, rnd_pan, 0)

    p.connect(r_scat, 0, mul_sc, 0)
    p.connect(rnd_pos, 0, sc_rnd, 0)
    p.connect(sc_rnd, 0, off_rnd, 0)
    p.connect(off_rnd, 0, mul_sc, 1)
    p.connect(r_pos, 0, pos_sum, 0)
    p.connect(mul_sc, 0, pos_sum, 1)
    p.connect(pos_sum, 0, clip_pos, 0)
    p.connect(clip_pos, 0, buf_pos, 0)
    p.connect(buf_pos, 0, add_pos, 1)   # set start offset

    p.connect(r_size, 0, freq_obj, 0)
    p.connect(freq_obj, 0, phasor, 0)
    p.connect(freq_obj, 0, env_ph, 0)
    p.connect(phasor, 0, scale_ph, 0)
    p.connect(scale_ph, 0, add_pos, 0)
    p.connect(add_pos, 0, reader, 0)

    p.connect(env_ph, 0, pi_mul, 0)
    p.connect(pi_mul, 0, sin_env, 0)
    p.connect(sin_env, 0, env_inv, 0)
    p.connect(env_inv, 0, env_off, 0)
    p.connect(reader, 0, apply_env, 0)
    p.connect(env_off, 0, apply_env, 1)

    p.connect(r_pan, 0, mul_pan, 0)
    p.connect(rnd_pan, 0, sc_pan, 0)
    p.connect(sc_pan, 0, off_pan, 0)
    p.connect(off_pan, 0, mul_pan, 1)

    # pan_L amplitude = 0.5 + 0.5*pan, pan_R = 0.5 - 0.5*pan
    p.connect(apply_env, 0, pan_L, 0)
    p.connect(apply_env, 0, pan_R, 0)
    p.connect(mul_pan, 0, inv_pan, 0)   # using signal for pan
    p.connect(inv_pan, 0, off_panR, 0)
    p.connect(off_panR, 0, pan_R, 1)
    p.connect(pan_L, 0, sL, 0)
    p.connect(pan_R, 0, sR, 0)

    return p.render()


# ── MIXER + FX ──────────────────────────────────────────────────────────────
def mixer_fx():
    p = Patch()

    # receive 4 stereo voice outputs and sum them
    voices_L = [p.add(f"#X obj {10+i*80} 10 r~ vout{i+1}-L;") for i in range(4)]
    voices_R = [p.add(f"#X obj {10+i*80} 40 r~ vout{i+1}-R;") for i in range(4)]

    sum1L = p.add("#X obj 10 80 +~;")
    sum2L = p.add("#X obj 10 110 +~;")
    sumL  = p.add("#X obj 10 140 +~;")
    sum1R = p.add("#X obj 200 80 +~;")
    sum2R = p.add("#X obj 200 110 +~;")
    sumR  = p.add("#X obj 200 140 +~;")

    p.connect(voices_L[0], 0, sum1L, 0)
    p.connect(voices_L[1], 0, sum1L, 1)
    p.connect(voices_L[2], 0, sum2L, 0)
    p.connect(voices_L[3], 0, sum2L, 1)
    p.connect(sum1L, 0, sumL, 0)
    p.connect(sum2L, 0, sumL, 1)
    p.connect(voices_R[0], 0, sum1R, 0)
    p.connect(voices_R[1], 0, sum1R, 1)
    p.connect(voices_R[2], 0, sum2R, 0)
    p.connect(voices_R[3], 0, sum2R, 1)
    p.connect(sum1R, 0, sumR, 0)
    p.connect(sum2R, 0, sumR, 1)

    # filter: lop~ (1-pole lowpass) controlled by CC34
    r_fc   = p.add("#X obj 10 190 r filter-freq;")
    sc_fc  = p.add("#X obj 10 220 expr $f1 * 0.007874 * 18000 + 80;")
    lopL   = p.add("#X obj 10 260 lop~ 1000;")
    lopR   = p.add("#X obj 200 260 lop~ 1000;")
    p.connect(r_fc, 0, sc_fc, 0)
    p.connect(sc_fc, 0, lopL, 1)
    p.connect(sc_fc, 0, lopR, 1)
    p.connect(sumL, 0, lopL, 0)
    p.connect(sumR, 0, lopR, 0)

    # distortion: gain + clip~
    r_dist  = p.add("#X obj 10 310 r distort-amt;")
    sc_dist = p.add("#X obj 10 340 expr $f1 * 0.007874 * 20 + 1;")
    distL   = p.add("#X obj 10 380 *~;")
    distR   = p.add("#X obj 200 380 *~;")
    clipL   = p.add("#X obj 10 410 clip~ -1 1;")
    clipR   = p.add("#X obj 200 410 clip~ -1 1;")
    p.connect(r_dist, 0, sc_dist, 0)
    p.connect(lopL, 0, distL, 0)
    p.connect(lopR, 0, distR, 0)
    p.connect(sc_dist, 0, distL, 1)
    p.connect(sc_dist, 0, distR, 1)
    p.connect(distL, 0, clipL, 0)
    p.connect(distR, 0, clipR, 0)

    # master volume with smooth line~
    r_vol  = p.add("#X obj 10 450 r master-vol;")
    sc_vol = p.add("#X obj 10 480 expr $f1 * 0.007874;")
    lineL  = p.add("#X obj 10 510 line~ 10;")
    lineR  = p.add("#X obj 200 510 line~ 10;")
    volL   = p.add("#X obj 10 550 *~;")
    volR   = p.add("#X obj 200 550 *~;")
    dac    = p.add("#X obj 10 590 dac~;")
    p.connect(r_vol, 0, sc_vol, 0)
    p.connect(sc_vol, 0, lineL, 0)
    p.connect(sc_vol, 0, lineR, 0)
    p.connect(clipL, 0, volL, 0)
    p.connect(clipR, 0, volR, 0)
    p.connect(lineL, 0, volL, 1)
    p.connect(lineR, 0, volR, 1)
    p.connect(volL, 0, dac, 0)
    p.connect(volR, 0, dac, 1)

    return p.render()


# ── ASSEMBLE MAIN PATCH ─────────────────────────────────────────────────────
def generate():
    out = []
    out.append("#N canvas 50 50 900 700 granular-noise 12;")
    out.append("#X text 10 5 GRANULAR NOISE - Pi Zero + RaspiAudio MIC+ - CC25-CC40;")

    sections = [
        ("MIDI-INPUT",    20,  40, midi_input),
        ("BUFFER",        20,  80, buffer_manager),
        ("SCHEDULER",     20, 120, scheduler),
        ("VOICE-1",       20, 160, lambda: voice(1)),
        ("VOICE-2",       20, 200, lambda: voice(2)),
        ("VOICE-3",       20, 240, lambda: voice(3)),
        ("VOICE-4",       20, 280, lambda: voice(4)),
        ("MIXER-FX",      20, 320, mixer_fx),
    ]

    for name, x, y, fn in sections:
        out.append(f"#N canvas 0 0 900 700 {name} 12;")
        out.extend(fn())
        out.append(f"#X restore {x} {y} pd {name};")

    return "\n".join(out) + "\n"


if __name__ == "__main__":
    patch_dir = os.path.join(os.path.dirname(__file__), "..", "pd")
    os.makedirs(patch_dir, exist_ok=True)
    out_path = os.path.join(patch_dir, "granular.pd")
    content = generate()
    with open(out_path, "w") as f:
        f.write(content)
    print(f"Patch généré : {out_path}")
    print(f"  {content.count(chr(10))} lignes")
