"""
🌀 HYPNOTIC BALLS — Générateur de vidéos verticales "oddly satisfying" (TikTok / Shorts / Reels)

Utilisation :
    python Hypnotic_balls.py                  -> 1 vidéo unique dans le dossier videos/
    python Hypnotic_balls.py --count 5        -> 5 vidéos différentes d'affilée
    python Hypnotic_balls.py --seed 123456    -> refait EXACTEMENT la même vidéo (seed affichée à chaque run)
    python Hypnotic_balls.py --draft          -> aperçu rapide (encodage léger, sans halo néon)
    python Hypnotic_balls.py --help           -> toutes les options
"""
import os
import sys
import random
import argparse
import shutil
import tempfile
import time
from datetime import datetime

# Empêche OpenBLAS / NumPy de réserver 300+ Mo de mémoire virtuelle par thread sur Windows !
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import numpy as np
import imageio_ffmpeg
import math
import colorsys
import wave
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

# Configure la console Windows en UTF-8 pour afficher les emojis sans erreur
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)  # + progression affichée en direct

# --- DOSSIER EXACT DU SCRIPT ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================================
# ⚙️ TABLEAU DE BORD : TES PARAMÈTRES À MODIFIER FACILEMENT
# ==========================================================
WIDTH, HEIGHT = 1080, 1920
FPS = 60
MAX_DURATION = 160          # ⏱️ Sécurité large (s'arrête automatiquement pile quand les 32 anneaux sont cassés !)
OUTRO_SECONDS = 2.8         # 🎆 Temps d'apothéose finale après le dernier anneau cassé

NUM_RINGS = 32              # ⭕ Nombre d'anneaux
BASE_RADIUS = 85            # Rayon du 1er petit anneau au centre
RING_SPACING = 14           # Espace entre chaque anneau
RING_THICKNESS = 6          # Épaisseur du trait des anneaux
GAP_SIZE = math.pi / 3.9    # Taille de la sortie

# 🌀 ANNEAUX MÊME DIRECTION + LATENCE PROGRESSIVE (EFFET VAGUE HYPNOTIQUE)
SAME_DIRECTION = True       # True = Aucun anneau inversé ! Tous tournent dans le même sens.
RING_BASE_SPEED = 0.021     # 🔄 Vitesse douce et hypnotique du 1er anneau au centre
RING_LATENCY_SPEED = 0.00030 # ⏳ Latence de vitesse entre chaque anneau (chaque anneau extérieur a un léger retard)
RING_LATENCY_ANGLE = 0.25   # 📐 Décalage d'angle initial entre chaque anneau (forme une grande vague spirale)

# 🧘 PHYSIQUE HARMONIQUE & HYPNOTIQUE (Zéro frôlement, rebonds profonds, vitesse calme)
START_GRAVITY = 0.14        # 🌍 Gravité très douce au début (effet flottant / pendulaire)
END_GRAVITY = 0.28          # 🌍 Gravité en fin de vidéo (reste fluide et jamais chaotique)
START_MIN_SPEED = 5.6       # 🐢 Vitesse minimale au début (très douce et lisible)
END_MIN_SPEED = 14.5        # ⚡ Vitesse minimale à la fin (rythmée mais toujours hypnotique)
START_MAX_SPEED = 7.4       # Plafond de vitesse au début
END_MAX_SPEED = 17.5        # Plafond de vitesse à la fin
SPEED_CURVE_EXP = 1.20      # Courbe d'accélération harmonieuse
RESTITUTION = 1.015         # Léger entretien d'énergie par rebond

BALL_RADIUS = 15            # Taille initiale de la balle
BALL_GROWTH_PER_RING = 0.18 # 📈 La balle grossit subtilement à chaque anneau détruit

# 🎲 ALÉATOIRE TOTAL (CHAQUE VIDÉO GÉNÉRÉE EST 100% UNIQUE)
RANDOMIZE_EACH_VIDEO = True # Change les couleurs, la latence, la mélodie, le suspense et le départ à chaque run !

# 🌟 EFFETS VISUELS HYPNOTIQUES & DOUX (INTERNATIONAL / ENGLISH UI)
ENABLE_SCREEN_SHAKE = True  # 📳 Micro-vibration douce uniquement lors de la cassure d'un anneau
ENABLE_SHOCKWAVES = True    # 🌊 Onde harmonique circulaire à chaque rebond et chaque cassure
ENABLE_SHARDS = True        # 💥 L'anneau se dissout en éclats physiques qui tombent doucement
ENABLE_SPARKS = True        # ✨ Poussière d'étoiles douce aux impacts
ENABLE_HUD_COUNTER = True   # 🎯 Interface en ANGLAIS (RINGS LEFT, COMBO, SATISFYING...)
ENABLE_STARFIELD = True     # 🌌 Fond étoilé hypnotique en rotation lente

# 🆕 V4 : RENDU "NÉON PREMIUM", SUSPENSE FINAL & SON SPATIAL
ENABLE_BLOOM = True         # 💡 Halo néon lumineux (bloom) autour des anneaux, de la balle et des éclats
BLOOM_STRENGTH = 0.80       #    Intensité du halo (0.0 = aucun, 1.0 = très lumineux)
BLOOM_RADIUS = 5            #    Diffusion du halo (en pixels, sur l'image réduite 1/4)
ENABLE_NEBULA_BG = True     # 🌌 Fond dégradé "nébuleuse" + vignette (au lieu d'un fond uni)
ENABLE_GAP_MARKERS = True   # 🔦 Petites lumières aux bords de la sortie de l'anneau actif (on anticipe la cassure)
ENABLE_FINAL_TENSION = True # 💓 Quand il reste ≤ 3 anneaux : battements de cœur + vignette rouge + "FINAL RING"
TENSION_RINGS = 3
ENABLE_LOOP_FADE = True     # 🔁 Fondu au noir au début et à la fin -> boucle parfaite sur TikTok/Shorts
FADE_IN_SECONDS = 0.6
FADE_OUT_SECONDS = 0.8
ENABLE_STEREO = True        # 🎧 Son stéréo : chaque note sort à gauche/droite selon la position de la balle
ENABLE_REVERB = True        # 🎧 Réverbération douce (effet "grande salle" hypnotique)
REVERB_WET = 0.35
ENABLE_AMBIENT_PAD = True   # 🎹 Nappe sonore ambiante qui "respire" et monte avec la progression
PAD_VOLUME = 0.10

# 💾 EXPORT
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "videos")  # 📁 Les vidéos vont ici (dossier ignoré par Git -> jamais envoyé sur GitHub)
OPEN_FOLDER_WHEN_DONE = True # Ouvre l'explorateur Windows sur la vidéo à la fin
VIDEO_PRESET = "veryfast"   # Encodage plus efficace que "ultrafast" -> fichier ~3x plus léger pour l'upload
VIDEO_CRF = 20              # Qualité (18 = quasi parfait, 23 = plus léger)
# ==========================================================

CENTER = np.array([WIDTH / 2, HEIGHT / 2 + 40], dtype=float)
SAMPLE_RATE = 44100

# Accroches psychologiques en ANGLAIS en haut de la vidéo pour retenir l'audience internationale
# ⚠️ Pas d'emojis dans le texte de la vidéo : la police Segoe UI Bold ne les contient pas
# et ils s'affichaient en carrés vides (□) !
ENGLISH_HOOKS = [
    "WAIT FOR THE LAST RING...",
    "99% CAN'T LOOK AWAY",
    "ODDLY SATISFYING ESCAPE",
    "WATCH UNTIL IT BREAKS FREE",
    "CAN YOU GUESS THE NEXT BREAK?",
    "DON'T BLINK...",
]

# --- MÉLODIES HYPNOTIQUES ---
MELODIES = {
    "Beethoven - Für Elise (Music Box)": [
        659.25, 622.25, 659.25, 622.25, 659.25, 493.88, 587.33, 523.25, 440.00,
        261.63, 329.63, 440.00, 493.88, 329.63, 415.30, 493.88, 523.25,
        329.63, 659.25, 622.25, 659.25, 622.25, 659.25, 493.88, 587.33, 523.25, 440.00,
        261.63, 329.63, 440.00, 493.88, 329.63, 523.25, 493.88, 440.00
    ],
    "Bach - Prelude in C Major (Crystal Harp)": [
        261.63, 329.63, 392.00, 523.25, 659.25, 392.00, 523.25, 659.25,
        261.63, 293.66, 440.00, 587.33, 698.46, 440.00, 587.33, 698.46,
        246.94, 293.66, 392.00, 587.33, 698.46, 392.00, 587.33, 698.46,
        261.63, 329.63, 392.00, 523.25, 659.25, 392.00, 523.25, 659.25
    ],
    "Satie - Gymnopédie No.1 (Dreamy Chimes)": [
        369.99, 440.00, 392.00, 369.99, 293.66, 246.94, 293.66, 277.18, 220.00,
        369.99, 440.00, 392.00, 369.99, 293.66, 246.94, 293.66, 277.18, 196.00,
        246.94, 293.66, 392.00, 369.99, 293.66, 329.63, 392.00, 369.99, 277.18
    ],
    "Tchaikovsky - Sugar Plum Fairy (Celesta)": [
        783.99, 659.25, 783.99, 739.99, 587.33, 659.25, 587.33, 587.33, 523.25, 523.25,
        493.88, 493.88, 440.00, 493.88, 523.25, 493.88, 659.25, 587.33, 659.25, 622.25
    ],
}

# Note fondamentale de la nappe ambiante (dans la tonalité de chaque morceau)
PAD_ROOTS = {
    "Beethoven - Für Elise (Music Box)": 110.00,          # La
    "Bach - Prelude in C Major (Crystal Harp)": 130.81,   # Do
    "Satie - Gymnopédie No.1 (Dreamy Chimes)": 146.83,    # Ré
    "Tchaikovsky - Sugar Plum Fairy (Celesta)": 164.81,   # Mi
}


# ==========================================================
# 🎵 AUDIO
# ==========================================================
def pan_from_x(x):
    """Position horizontale de la balle -> panoramique stéréo (-1 gauche ... +1 droite)."""
    return float(np.clip((x - CENTER[0]) / (WIDTH * 0.5), -1.0, 1.0)) * 0.75


class AudioMixer:
    """Buffer STÉRÉO (canal 0 = gauche, canal 1 = droite) + synthèse des notes, propre à chaque vidéo."""
    def __init__(self, max_seconds, pitch_factor):
        self.buffer = np.zeros((2, int((max_seconds + 5) * SAMPLE_RATE)), dtype=np.float32)
        self.pitch_factor = pitch_factor

    def mix(self, start_idx, signal, pan=0.0):
        """Ajoute un signal mono dans le buffer stéréo avec panoramique à puissance constante."""
        if not ENABLE_STEREO:
            pan = 0.0
        theta = (pan + 1.0) * math.pi / 4.0
        gain_l, gain_r = math.cos(theta) * 1.414, math.sin(theta) * 1.414
        n = len(signal)
        self.buffer[0, start_idx:start_idx + n] += (signal * gain_l).astype(np.float32)
        self.buffer[1, start_idx:start_idx + n] += (signal * gain_r).astype(np.float32)

    def piano_note(self, time_sec, freq, duration=0.80, volume=0.38, is_chord=False, combo_level=0, pan=0.0):
        """Synthèse harmonique douce type Boîte à Musique / Célesta avec résonance longue hypnotique."""
        start_idx = int(time_sec * SAMPLE_RATE)
        if start_idx >= self.buffer.shape[1]:
            return

        num_samples = min(int(duration * SAMPLE_RATE), self.buffer.shape[1] - start_idx)
        if num_samples <= 0:
            return
        t = np.linspace(0, num_samples / SAMPLE_RATE, num_samples, endpoint=False)

        # Attaque veloutée (pas de claquement sec) + longue résonance harmonique
        attack = np.minimum(1.0, t / 0.008)
        hammer_strike = 0.30 * np.exp(-25.0 * t)
        string_sustain = 0.70 * np.exp(-3.4 * t)
        envelope = attack * (hammer_strike + string_sustain)

        if is_chord:
            shimmer_mult = 2.0 + min(combo_level * 0.5, 1.5)
            # Rondeur de basse chaleureuse et profonde quand un anneau s'ouvre
            warm_bass = 0.30 * np.sin(2 * np.pi * (freq * 0.5) * t) * np.exp(-3.8 * t)
            crystal_shimmer = 0.12 * np.sin(2 * np.pi * (freq * 3.0) * t) * np.exp(-9.0 * t)

            wave_sig = (
                0.45 * np.sin(2 * np.pi * (freq * 0.5) * t) +
                0.42 * np.sin(2 * np.pi * freq * t) +
                0.26 * np.sin(2 * np.pi * (freq * 1.498) * t) +
                0.18 * np.sin(2 * np.pi * (freq * shimmer_mult) * t) +
                crystal_shimmer
            ) * envelope + warm_bass
        else:
            wave_sig = (
                0.62 * np.sin(2 * np.pi * freq * t) +
                0.16 * np.sin(2 * np.pi * (freq * 1.0012) * t) +
                0.22 * np.sin(2 * np.pi * (freq * 2.0) * t) * np.exp(-2.8 * t) +
                0.10 * np.sin(2 * np.pi * (freq * 3.0) * t) * np.exp(-5.5 * t)
            ) * envelope

        self.mix(start_idx, wave_sig * volume, pan)

    def victory_fanfare(self, time_sec):
        """Grand accord final céleste quand tous les anneaux sont détruits !"""
        chord_freqs = [261.63, 329.63, 392.00, 523.25, 659.25, 783.99, 1046.50]
        for idx, f in enumerate(chord_freqs):
            # L'arpège "s'ouvre" de gauche à droite dans le casque
            sweep_pan = -0.7 + 1.4 * idx / (len(chord_freqs) - 1)
            self.piano_note(time_sec + idx * 0.065, f * self.pitch_factor, duration=2.4, volume=0.34,
                            is_chord=True, combo_level=idx, pan=sweep_pan)

    def heartbeat(self, time_sec, volume=0.55):
        """Battement de cœur grave (lub-dub) pour la tension des derniers anneaux."""
        for offset, vol in ((0.0, 1.0), (0.17, 0.7)):
            start_idx = int((time_sec + offset) * SAMPLE_RATE)
            num_samples = min(int(0.32 * SAMPLE_RATE), self.buffer.shape[1] - start_idx)
            if num_samples <= 0:
                continue
            t = np.arange(num_samples) / SAMPLE_RATE
            # Sinus grave avec chute de hauteur (effet "thump" organique)
            freq_sweep = 62.0 * np.exp(-6.0 * t) + 38.0
            phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE
            env = np.minimum(1.0, t / 0.004) * np.exp(-14.0 * t)
            self.mix(start_idx, np.sin(phase) * env * volume * vol, 0.0)


def build_ambient_pad(num_samples, progress_curve, pad_root):
    """Nappe ambiante (fondamentale + quinte + octave) qui respire lentement et s'intensifie avec la progression.
    Générée par blocs d'1 seconde -> aucun pic de RAM."""
    pad = np.zeros(num_samples, dtype=np.float32)
    voices = [(pad_root, 1.0), (pad_root * 1.5, 0.55), (pad_root * 2.0, 0.40), (pad_root * 2.003, 0.30)]
    block = SAMPLE_RATE
    frame_times = np.arange(len(progress_curve)) / FPS
    total_sec = num_samples / SAMPLE_RATE
    for start in range(0, num_samples, block):
        end = min(start + block, num_samples)
        t = np.arange(start, end) / SAMPLE_RATE
        sig = np.zeros(end - start)
        for f, a in voices:
            sig += a * np.sin(2 * np.pi * f * t)
        breathing = 0.65 + 0.35 * np.sin(2 * np.pi * 0.09 * t)           # respiration lente ~11 s
        prog = np.interp(t, frame_times, progress_curve) if len(progress_curve) else 0.0
        intensity = 0.45 + 0.75 * prog                                    # monte avec la progression
        fade = np.minimum(1.0, t / 3.0) * np.clip((total_sec - t) / 1.5, 0.0, 1.0)
        pad[start:end] = (sig * breathing * intensity * fade * PAD_VOLUME).astype(np.float32)
    return pad


def _feedback_delay(x, delay, gain):
    """y[n] = x[n] + gain * y[n - delay], vectorisé par blocs de taille 'delay' (rapide et léger)."""
    y = x.copy()
    n = len(y)
    for start in range(delay, n, delay):
        end = min(start + delay, n)
        y[start:end] += gain * y[start - delay:end - delay]
    return y


def _allpass(x, delay, gain):
    y = -gain * x
    y[delay:] += x[:-delay]
    n = len(y)
    for start in range(delay, n, delay):
        end = min(start + delay, n)
        y[start:end] += gain * y[start - delay:end - delay]
    return y


def apply_reverb(channel, stereo_offset=0):
    """Réverbération de type Schroeder/Freeverb (4 filtres en peigne + 2 passe-tout)."""
    combs = [1116, 1188, 1277, 1356]
    wet = np.zeros_like(channel)
    for d in combs:
        wet += _feedback_delay(channel, d + stereo_offset, 0.84)
    for d in (556, 441):
        wet = _allpass(wet, d + stereo_offset, 0.5)
    rms_dry = float(np.sqrt(np.mean(channel ** 2))) + 1e-9
    rms_wet = float(np.sqrt(np.mean(wet ** 2))) + 1e-9
    return channel + wet * (REVERB_WET * rms_dry / rms_wet)


def write_wav(path, stereo_buffer):
    audio_int16 = (np.clip(stereo_buffer, -1.0, 1.0).T * 32767).astype(np.int16)  # (échantillons, 2) -> entrelacé G/D
    with wave.open(path, "w") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(np.ascontiguousarray(audio_int16).tobytes())


# ==========================================================
# 🎨 VISUELS
# ==========================================================
def load_font(size):
    """Charge une police propre sur Windows (Segoe UI / Arial Bold) ou police par défaut."""
    for font_name in ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


FONT_HOOK = load_font(32)
FONT_TITLE = load_font(44)
FONT_SUB = load_font(26)
FONT_COMBO = load_font(44)
FONT_VICTORY = load_font(66)


def hsv_color(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


class Ring:
    def __init__(self, index, radius, gap_angle_size, speed, hue, start_angle):
        self.index = index
        self.radius = radius
        self.gap_size = gap_angle_size
        self.angle = start_angle
        self.speed = speed
        self.active = True
        self.hue = hue

        rgb = hsv_color(hue, 0.80, 1.0)
        self.color = (*rgb, 255)
        self.glow_color = (*rgb, 65)
        self.thickness = RING_THICKNESS
        self.hit_flash = 0.0
        # Correction de phase douce (remplace l'ancien "saut" d'angle visible à l'œil nu)
        self.correction_left = 0.0
        self.correction_frames = 0

    def schedule_correction(self, delta_angle, frames):
        """Fait glisser l'anneau en douceur de delta_angle radians sur 'frames' images."""
        self.correction_left = delta_angle
        self.correction_frames = max(1, int(frames))

    def update(self):
        if self.active:
            extra = 0.0
            if self.correction_frames > 0:
                extra = self.correction_left / self.correction_frames
                self.correction_left -= extra
                self.correction_frames -= 1
            self.angle = (self.angle + self.speed + extra) % (2 * math.pi)
            if self.hit_flash > 0:
                self.hit_flash = max(0.0, self.hit_flash - 0.08)

    def draw(self, draw_ctx, offset, is_innermost=False, pulse_phase=0.0):
        if not self.active:
            return
        cx, cy = CENTER[0] + offset[0], CENTER[1] + offset[1]
        start_deg = math.degrees(self.angle + self.gap_size / 2)
        end_deg = math.degrees(self.angle + 2 * math.pi - self.gap_size / 2)
        bbox = [cx - self.radius, cy - self.radius, cx + self.radius, cy + self.radius]

        # Respiration lumineuse lente sur l'anneau intérieur
        if is_innermost or self.hit_flash > 0:
            pulse_extra = int(3 * math.sin(pulse_phase * 4.5)) if is_innermost else 0
            glow_w = self.thickness + 8 + pulse_extra + int(self.hit_flash * 9)
            draw_ctx.arc(bbox, start=start_deg, end=end_deg, fill=self.glow_color, width=glow_w)

        if self.hit_flash > 0:
            r = int(self.color[0] + (255 - self.color[0]) * self.hit_flash)
            g = int(self.color[1] + (255 - self.color[1]) * self.hit_flash)
            b = int(self.color[2] + (255 - self.color[2]) * self.hit_flash)
            draw_color = (r, g, b, 255)
        else:
            draw_color = self.color

        draw_ctx.arc(bbox, start=start_deg, end=end_deg, fill=draw_color, width=self.thickness)

        # 🔦 Lumières aux deux bords de la sortie de l'anneau actif
        if ENABLE_GAP_MARKERS and is_innermost:
            glow_pulse = 0.5 + 0.5 * math.sin(pulse_phase * 5.0)
            for edge in (self.angle + self.gap_size / 2, self.angle - self.gap_size / 2):
                ex = cx + math.cos(edge) * self.radius
                ey = cy + math.sin(edge) * self.radius
                halo = self.thickness * (1.3 + 0.5 * glow_pulse)
                draw_ctx.ellipse([ex - halo, ey - halo, ex + halo, ey + halo], fill=(*self.color[:3], 110))
                core = self.thickness * 0.75
                draw_ctx.ellipse([ex - core, ey - core, ex + core, ey + core], fill=(255, 255, 255, 235))


class RingShard:
    """Fragment d'arc physique harmonieux quand un anneau s'ouvre."""
    def __init__(self, radius, start_rad, end_rad, color):
        self.radius = radius
        self.span = end_rad - start_rad
        mid_angle = (start_rad + end_rad) / 2.0
        self.pos = np.array([
            CENTER[0] + math.cos(mid_angle) * radius,
            CENTER[1] + math.sin(mid_angle) * radius
        ], dtype=float)

        out_speed = np.random.uniform(2.2, 6.2)
        self.vel = np.array([
            math.cos(mid_angle) * out_speed + np.random.uniform(-1.2, 1.2),
            math.sin(mid_angle) * out_speed - np.random.uniform(0.5, 2.5)
        ], dtype=float)
        self.rot = mid_angle
        self.rot_speed = np.random.uniform(-0.08, 0.08)
        self.color = color[:3]
        self.life = 240.0
        self.decay = np.random.uniform(4.5, 7.5)
        self.seg_len = max(12.0, radius * self.span * 0.45)

    def update(self, current_gravity):
        self.vel[1] += current_gravity * 0.45
        self.pos += self.vel
        self.rot += self.rot_speed
        self.life -= self.decay

    def draw(self, draw_ctx, offset):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(self.life)))
        cx, cy = self.pos[0] + offset[0], self.pos[1] + offset[1]
        dx = math.cos(self.rot + math.pi / 2) * (self.seg_len / 2)
        dy = math.sin(self.rot + math.pi / 2) * (self.seg_len / 2)
        p1 = (cx - dx, cy - dy)
        p2 = (cx + dx, cy + dy)
        draw_ctx.line([p1, p2], fill=(*self.color, alpha // 3), width=RING_THICKNESS + 5)
        draw_ctx.line([p1, p2], fill=(*self.color, alpha), width=RING_THICKNESS)


class Shockwave:
    """Onde harmonique circulaire qui se propage tout en douceur."""
    def __init__(self, x, y, start_radius, color, max_expand=95, start_life=190.0):
        self.pos = np.array([x, y], dtype=float)
        self.radius = float(start_radius)
        self.max_radius = float(start_radius + max_expand)
        self.color = color[:3]
        self.life = start_life
        self.max_life = start_life

    def update(self):
        self.radius += (self.max_radius - self.radius) * 0.12 + 1.8
        self.life -= 8.5

    def draw(self, draw_ctx, offset):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(self.life)))
        cx, cy = self.pos[0] + offset[0], self.pos[1] + offset[1]
        bbox = [cx - self.radius, cy - self.radius, cx + self.radius, cy + self.radius]
        width = max(1, int((self.life / self.max_life) * 5))
        draw_ctx.ellipse(bbox, outline=(*self.color, alpha), width=width)


class Particle:
    """Particules douces et poussière d'étoiles."""
    def __init__(self, x, y, color, speed_range=(2, 7.5), angle_center=None, angle_spread=2*math.pi, size_range=(2.5, 5.5), is_spark=False):
        self.pos = np.array([x, y], dtype=float)
        self.prev_pos = self.pos.copy()
        if angle_center is None:
            angle = np.random.uniform(0, 2 * math.pi)
        else:
            angle = np.random.uniform(angle_center - angle_spread / 2, angle_center + angle_spread / 2)
        speed = np.random.uniform(*speed_range)
        self.vel = np.array([math.cos(angle) * speed, math.sin(angle) * speed], dtype=float)
        self.color = color[:3]
        self.life = 235.0
        self.decay = np.random.uniform(6.0, 10.5) if is_spark else np.random.uniform(4.2, 7.5)
        self.radius = np.random.uniform(*size_range)
        self.is_spark = is_spark

    def update(self, current_gravity):
        self.prev_pos = self.pos.copy()
        self.vel[1] += current_gravity * (0.28 if self.is_spark else 0.20)
        self.vel *= 0.96
        self.pos += self.vel
        self.life -= self.decay

    def draw(self, draw_ctx, offset):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(self.life)))
        ox, oy = offset
        if self.is_spark:
            p1 = (self.prev_pos[0] + ox, self.prev_pos[1] + oy)
            p2 = (self.pos[0] + ox, self.pos[1] + oy)
            draw_ctx.line([p1, p2], fill=(255, 255, 255, alpha), width=2)
            draw_ctx.line([p1, p2], fill=(*self.color, alpha // 2), width=4)
        else:
            r = self.radius * (0.4 + 0.6 * (self.life / 235.0))
            bbox = [self.pos[0] + ox - r, self.pos[1] + oy - r, self.pos[0] + ox + r, self.pos[1] + oy + r]
            draw_ctx.ellipse(bbox, fill=(*self.color, alpha))


class FloatingText:
    """Texte flottant en ANGLAIS (ex: COMBO x3, PERFECT)"""
    def __init__(self, text, x, y, color, size_font=FONT_COMBO):
        self.text = text
        self.pos = np.array([x, y], dtype=float)
        self.vel = np.array([0.0, -2.4], dtype=float)
        self.color = color[:3]
        self.life = 235.0
        self.font = size_font

    def update(self):
        self.pos += self.vel
        self.vel *= 0.95
        self.life -= 5.5

    def draw(self, draw_ctx, offset):
        if self.life <= 0:
            return
        alpha = max(0, min(255, int(self.life)))
        x, y = self.pos[0] + offset[0], self.pos[1] + offset[1]
        draw_ctx.text((x + 2, y + 2), self.text, font=self.font, fill=(0, 0, 0, alpha // 2), anchor="mm")
        draw_ctx.text((x, y), self.text, font=self.font, fill=(*self.color, alpha), anchor="mm")


def update_and_draw(objects, draw_ctx, offset, *update_args):
    """Met à jour + dessine une liste d'effets, et renvoie seulement ceux encore vivants (rapide, sans list.remove)."""
    alive = []
    for obj in objects:
        obj.update(*update_args)
        obj.draw(draw_ctx, offset)
        if obj.life > 0:
            alive.append(obj)
    return alive


def build_nebula_background(hue_offset):
    """Fond pré-calculé UNE SEULE FOIS : dégradé radial teinté (couleur aléatoire) + vignette sombre."""
    if not ENABLE_NEBULA_BG:
        return Image.new("RGB", (WIDTH, HEIGHT), (8, 8, 16))
    ys = np.arange(HEIGHT, dtype=np.float32)[:, None]
    xs = np.arange(WIDTH, dtype=np.float32)[None, :]
    d = np.sqrt(((xs - CENTER[0]) / (WIDTH * 0.75)) ** 2 + ((ys - CENTER[1]) / (HEIGHT * 0.55)) ** 2)
    glow = np.clip(1.0 - d, 0.0, 1.0) ** 2.2
    tint = colorsys.hsv_to_rgb((hue_offset + 0.62) % 1.0, 0.65, 1.0)
    base = np.array([6, 6, 13], dtype=np.float32)
    rgb = base[None, None, :] + glow[:, :, None] * np.array(tint, dtype=np.float32)[None, None, :] * 34.0
    vignette = np.clip(1.15 - d * 0.55, 0.55, 1.0)
    rgb *= vignette[:, :, None]
    # Tramage (dithering) : supprime les "bandes" visibles dans les dégradés sombres
    rgb += np.random.uniform(-0.6, 0.6, size=rgb.shape).astype(np.float32)
    rgb = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, "RGB")


def apply_bloom(img):
    """Halo néon : image réduite 1/4 -> flou -> agrandie -> mélange 'screen'. Rapide et sans fuite mémoire."""
    small = img.reduce(4).filter(ImageFilter.GaussianBlur(BLOOM_RADIUS))
    small = ImageEnhance.Brightness(small).enhance(BLOOM_STRENGTH * 1.6)
    glow = small.resize((WIDTH, HEIGHT), Image.BILINEAR)
    img.paste(ImageChops.screen(img, glow))


def predict_best_arc(pos, target_speed, inward, current_gravity, ring, ball_radius):
    """🔮 Teste des arches franches (plusieurs angles ET vitesses) et renvoie celle qui retombe le plus près de la brèche.
    Calcul en float pur (sans petits tableaux NumPy) -> ~10x plus rapide qu'avant."""
    cx, cy = CENTER[0], CENTER[1]
    limit = ring.radius - ring.thickness / 2 - ball_radius
    limit_sq = limit * limit
    inward_ang = math.atan2(inward[1], inward[0])
    best_vel = None
    best_err = 999.0
    best_step = 40
    best_land_ang = 0.0
    for speed_mult in (1.0, 0.90, 1.10):
        test_spd = target_speed * speed_mult
        for delta_a in np.linspace(-0.72, 0.72, 25):
            test_a = inward_ang + delta_a
            tvx, tvy = math.cos(test_a) * test_spd, math.sin(test_a) * test_spd
            px, py = float(pos[0]), float(pos[1])
            vx, vy = tvx, tvy
            for step in range(1, 135):
                vy += current_gravity
                px += vx
                py += vy
                dx, dy = px - cx, py - cy
                if dx * dx + dy * dy >= limit_sq:
                    land_ang = math.atan2(dy, dx) % (2 * math.pi)
                    pred_ring_ang = (ring.angle + ring.speed * step) % (2 * math.pi)
                    err = abs((land_ang - pred_ring_ang + math.pi) % (2 * math.pi) - math.pi)
                    if err < best_err:
                        best_err = err
                        best_vel = np.array([tvx, tvy])
                        best_step = step
                        best_land_ang = land_ang
                    break
        if best_err < (ring.gap_size / 2) * 0.5:
            break  # Arche déjà parfaite, inutile de tester d'autres vitesses
    return best_vel, best_err, best_step, best_land_ang


# ==========================================================
# 🎬 GÉNÉRATION D'UNE VIDÉO
# ==========================================================
def generate_video(seed, output_path, preset=VIDEO_PRESET, crf=VIDEO_CRF, bloom=ENABLE_BLOOM, max_duration=MAX_DURATION):
    """Simule, dessine et encode UNE vidéo complète. Renvoie la durée (s) ou lève une exception en cas d'échec."""
    np.random.seed(seed)
    random.seed(seed)

    # Direction globale (horaire ou anti-horaire) et latence légèrement variée à chaque vidéo
    global_rot_dir = 1 if np.random.rand() > 0.5 else -1
    latency_angle_step = RING_LATENCY_ANGLE * np.random.uniform(0.90, 1.12)
    latency_speed_step = RING_LATENCY_SPEED * np.random.uniform(0.92, 1.10)
    hue_offset = np.random.uniform(0.0, 1.0)
    hue_direction = 1 if np.random.rand() > 0.5 else -1
    chosen_hook = random.choice(ENGLISH_HOOKS)

    melody_name, base_melody = random.choice(list(MELODIES.items()))
    semitone_shift = random.choice([-2, -1, 0, 1]) if RANDOMIZE_EACH_VIDEO else 0
    pitch_factor = 2.0 ** (semitone_shift / 12.0)
    melody_freqs = [f * pitch_factor for f in base_melody]
    note_index = 0
    pad_root = PAD_ROOTS.get(melody_name, 130.81) * pitch_factor
    audio = AudioMixer(max_duration, pitch_factor)

    # --- INITIALISATION DE LA BALLE & DES ANNEAUX AVEC LATENCE HARMONIQUE ---
    pos = CENTER + np.random.uniform(-8.0, 8.0, size=2)
    init_angle = np.random.uniform(-math.pi * 0.75, -math.pi * 0.25)
    init_speed = np.random.uniform(5.6, 6.4)
    vel = np.array([math.cos(init_angle) * init_speed, math.sin(init_angle) * init_speed], dtype=float)
    ball_hue = np.random.uniform(0.0, 1.0)
    current_ball_radius = float(BALL_RADIUS)

    rings = []
    base_spiral_angle = np.random.uniform(0, 2 * math.pi)
    for i in range(NUM_RINGS):
        r = BASE_RADIUS + i * RING_SPACING
        dir_mult = global_rot_dir if SAME_DIRECTION else (1 if i % 2 == 0 else -1)
        start_ang = (base_spiral_angle - i * latency_angle_step * dir_mult) % (2 * math.pi)
        rot_speed = (RING_BASE_SPEED - i * latency_speed_step) * dir_mult
        hue = (hue_offset + hue_direction * (i / NUM_RINGS)) % 1.0
        rings.append(Ring(index=i, radius=r, gap_angle_size=GAP_SIZE, speed=rot_speed, hue=hue, start_angle=start_ang))
    ring_cursor = 0  # Index du 1er anneau encore actif (les anneaux cassent toujours de l'intérieur vers l'extérieur)

    stars = []
    if ENABLE_STARFIELD:
        for _ in range(95):
            s_dist = np.random.uniform(40, max(WIDTH, HEIGHT) * 0.65)
            s_angle = np.random.uniform(0, 2 * math.pi)
            s_speed = np.random.uniform(0.0006, 0.0018) * global_rot_dir
            s_size = np.random.uniform(1.2, 2.8)
            s_alpha = np.random.randint(45, 145)
            stars.append([s_dist, s_angle, s_speed, s_size, s_alpha])

    particles = []
    shards = []
    shockwaves = []
    floating_texts = []
    trail_positions = []

    screen_shake = 0.0
    bg_flash = 0.0
    bg_flash_color = (255, 255, 255)
    combo_count = 0
    bounces_on_current_ring = 0
    # Suspense imprévisible : même au début, la balle fait au moins 2 rebonds sur le 1er anneau avant de pouvoir sortir !
    target_bounces_for_ring = np.random.randint(2, 5)
    last_break_time = -10.0
    all_broken_frame = None
    outro_frames_total = int(OUTRO_SECONDS * FPS)
    next_heartbeat_time = None   # 💓 Prochain battement de cœur (phase de tension finale)
    heartbeat_flash = 0.0        # Intensité de la vignette rouge synchronisée au cœur
    progress_curve = []          # Progression enregistrée à chaque image (pour la nappe ambiante)
    max_frames = FPS * max_duration

    sens_str = "Horaire ↻" if global_rot_dir > 0 else "Anti-Horaire ↺"
    print(f"🎲 Seed #{seed} | Sens : {sens_str} | Musique : {melody_name} | Accroche : {chosen_hook}")
    print("1/3 - Simulation & génération vidéo...")

    # Fichiers temporaires dans un dossier unique -> plusieurs générations en parallèle sans conflit
    work_dir = tempfile.mkdtemp(prefix=f"hypnotic_{seed}_")
    temp_video = os.path.join(work_dir, "video.mp4")
    temp_audio = os.path.join(work_dir, "audio.wav")
    ffmpeg_log_path = os.path.join(work_dir, "ffmpeg.log")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    video_pipe = None
    ffmpeg_log = open(ffmpeg_log_path, "w", encoding="utf-8", errors="replace")
    try:
        video_pipe = subprocess.Popen([
            ffmpeg_exe, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-pix_fmt", "rgb24",
            "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", preset,
            "-threads", "1",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            temp_video
        ], stdin=subprocess.PIPE, stderr=ffmpeg_log)

        background_img = build_nebula_background(hue_offset)

        # UNE SEULE image réutilisée pour toutes les frames -> 0 fuite de RAM / 0 MemoryError !
        frame_img = Image.new("RGB", (WIDTH, HEIGHT), (8, 8, 16))
        draw = ImageDraw.Draw(frame_img, "RGBA")

        render_start = time.perf_counter()
        frame = 0
        while frame < max_frames:
            current_time = frame / FPS
            while ring_cursor < NUM_RINGS and not rings[ring_cursor].active:
                ring_cursor += 1
            rem_now = NUM_RINGS - ring_cursor
            progress = ring_cursor / float(NUM_RINGS)  # 0.0 au début -> 1.0 à la fin

            # 🧘 COURBE D'ACCÉLÉRATION DOUCE ET HYPNOTIQUE
            curve = progress ** SPEED_CURVE_EXP
            current_gravity = START_GRAVITY + (END_GRAVITY - START_GRAVITY) * curve
            dynamic_min_speed = START_MIN_SPEED + (END_MIN_SPEED - START_MIN_SPEED) * curve
            dynamic_max_speed = START_MAX_SPEED + (END_MAX_SPEED - START_MAX_SPEED) * curve

            if ENABLE_SCREEN_SHAKE and screen_shake > 0.15:
                shake_offset = (
                    np.random.uniform(-screen_shake, screen_shake),
                    np.random.uniform(-screen_shake, screen_shake)
                )
                screen_shake *= 0.82
            else:
                shake_offset = (0.0, 0.0)
                screen_shake = 0.0

            # Fond nébuleuse pré-calculé (copie ultra-rapide) + flash coloré doux à chaque cassure
            frame_img.paste(background_img)
            if bg_flash > 0.01:
                fa = int(min(1.0, bg_flash) * 0.16 * 255)
                draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(*bg_flash_color[:3], fa))
                bg_flash *= 0.88
            progress_curve.append(progress)

            # 1. Champ d'étoiles hypnotique
            if ENABLE_STARFIELD:
                for s in stars:
                    s[1] += s[2] * (1.0 + curve * 1.2)
                    sx = CENTER[0] + math.cos(s[1]) * s[0] + shake_offset[0] * 0.25
                    sy = CENTER[1] + math.sin(s[1]) * s[0] + shake_offset[1] * 0.25
                    if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                        r_s = s[3]
                        twinkle = int(s[4] * (0.75 + 0.25 * math.sin(current_time * 3.0 + s[0])))
                        draw.ellipse([sx - r_s, sy - r_s, sx + r_s, sy + r_s], fill=(200, 220, 255, twinkle))

            # 2. Physique de la balle
            vel[1] += current_gravity
            pos += vel

            ball_hue = (ball_hue + 0.003) % 1.0
            ball_color = hsv_color(ball_hue, 0.72, 1.0)

            # Traînée comète soyeuse plus longue (28 positions)
            trail_positions.append((pos.copy(), ball_color, current_ball_radius))
            if len(trail_positions) > 28:
                trail_positions.pop(0)

            if rem_now > 0:
                current_ring = rings[ring_cursor]
                dist_vec = pos - CENTER
                dist = math.hypot(dist_vec[0], dist_vec[1])

                if dist + current_ball_radius >= current_ring.radius - current_ring.thickness / 2:
                    ball_angle = math.atan2(dist_vec[1], dist_vec[0]) % (2 * math.pi)
                    angle_diff = (ball_angle - current_ring.angle + math.pi) % (2 * math.pi) - math.pi

                    # Pour garder le suspense hypnotique : un anneau ne peut se casser que si la balle est dans la brèche ET a fait au moins son quota minimal de rebonds (1 à 3 rebonds aléatoires) !
                    if abs(angle_diff) < (current_ring.gap_size / 2) * 0.94 and bounces_on_current_ring >= max(1, target_bounces_for_ring - 1):
                        # 💥 ANNEAU CASSÉ !
                        current_ring.active = False
                        current_ball_radius += BALL_GROWTH_PER_RING
                        bounces_on_current_ring = 0
                        # Nouveau quota aléatoire de rebonds pour le prochain anneau (parfois 1 rebond, parfois 3 rebonds !)
                        target_bounces_for_ring = np.random.randint(1, 4)

                        if current_time - last_break_time < 1.6:
                            combo_count += 1
                        else:
                            combo_count = 1
                        last_break_time = current_time

                        cur_spd = math.hypot(vel[0], vel[1])
                        if 0 < cur_spd < dynamic_min_speed:
                            vel = (vel / cur_spd) * dynamic_min_speed

                        # Tremblement doux et satisfaisant (jamais agressif)
                        screen_shake = min(11.0, 3.5 + combo_count * 1.5)
                        bg_flash = min(0.85, 0.35 + combo_count * 0.08)
                        bg_flash_color = current_ring.color[:3]

                        freq = melody_freqs[note_index % len(melody_freqs)]
                        note_index += 1
                        audio.piano_note(current_time, freq=freq, duration=0.95, volume=0.45, is_chord=True, combo_level=combo_count, pan=pan_from_x(pos[0]))

                        if ENABLE_SHOCKWAVES:
                            shockwaves.append(Shockwave(CENTER[0], CENTER[1], current_ring.radius, current_ring.color, max_expand=80 + combo_count * 12))
                            shockwaves.append(Shockwave(pos[0], pos[1], current_ball_radius, (255, 255, 255), max_expand=60))

                        if ENABLE_SHARDS:
                            start_rad = current_ring.angle + current_ring.gap_size / 2
                            end_rad = current_ring.angle + 2 * math.pi - current_ring.gap_size / 2
                            num_shards = 16
                            arc_edges = np.linspace(start_rad, end_rad, num_shards + 1)
                            for s_i in range(num_shards):
                                shards.append(RingShard(current_ring.radius, arc_edges[s_i], arc_edges[s_i + 1], current_ring.color))

                        for theta in np.linspace(0, 2 * math.pi, 45):
                            px = CENTER[0] + current_ring.radius * math.cos(theta)
                            py = CENTER[1] + current_ring.radius * math.sin(theta)
                            particles.append(Particle(px, py, current_ring.color, speed_range=(2.0, 7.0)))

                        if combo_count >= 2:
                            floating_texts.append(
                                FloatingText(f"COMBO x{combo_count}", pos[0], pos[1] - 35, current_ring.color)
                            )

                        if rem_now - 1 == 0 and all_broken_frame is None:
                            all_broken_frame = frame
                            screen_shake = 16.0
                            bg_flash = 0.9
                            audio.victory_fanfare(current_time)
                            for _ in range(140):
                                c_col = hsv_color(np.random.rand(), 0.80, 1.0)
                                particles.append(Particle(pos[0], pos[1], c_col, speed_range=(4, 18), size_range=(3.5, 8.0), is_spark=(np.random.rand() > 0.4)))
                            shockwaves.append(Shockwave(CENTER[0], CENTER[1], current_ring.radius, (255, 255, 255), max_expand=360))
                            print(f"   🎉 Tous les anneaux ont été détruits à {current_time:.1f}s ! Génération du final...")

                    else:
                        # 🏓 REBOND HARMONIQUE & ANTI-FRÔLEMENT !
                        bounces_on_current_ring += 1
                        normal = dist_vec / (dist if dist > 0 else 1.0)

                        # Replace proprement la balle à l'intérieur de l'anneau
                        pos = CENTER + normal * (current_ring.radius - current_ring.thickness / 2 - current_ball_radius - 1.5)

                        # Calcul de la vitesse cible douce et progressive
                        target_speed = float(np.clip(math.hypot(vel[0], vel[1]) * RESTITUTION, dynamic_min_speed, dynamic_max_speed))

                        # Réflexion spéculaire naturelle
                        vel_nat = vel - 2 * np.dot(vel, normal) * normal
                        inward = -normal  # Vecteur pointant droit vers le centre du cercle
                        nat_len = math.hypot(vel_nat[0], vel_nat[1])
                        vel_dir = vel_nat / (nat_len if nat_len > 0 else 1.0)

                        # 🛡️ ANTI-FRÔLEMENT ABSOLU (Anti-Tangente) :
                        # Si l'angle du rebond est trop rasant (< 42 degrés par rapport à la paroi, soit cos < 0.66),
                        # on redresse franchement la trajectoire vers l'intérieur du cercle pour former une belle arche !
                        if np.dot(vel_dir, inward) < 0.66:
                            tangent = np.array([-normal[1], normal[0]])
                            t_sign = 1.0 if np.dot(vel_dir, tangent) >= 0 else -1.0
                            vel_dir = inward * 0.73 + tangent * (t_sign * 0.683)
                            vel_dir /= np.linalg.norm(vel_dir)

                        # Légère variation harmonique d'angle (-8° à +8°) pour que la trajectoire danse avec grâce
                        rot_jitter = np.random.uniform(-0.14, 0.14)
                        c_j, s_j = math.cos(rot_jitter), math.sin(rot_jitter)
                        vel_dir = np.array([vel_dir[0] * c_j - vel_dir[1] * s_j, vel_dir[0] * s_j + vel_dir[1] * c_j])
                        vel = vel_dir * target_speed

                        # 🔮 PRÉDICTION HARMONIQUE D'ARCHE :
                        # Quand l'anneau a atteint son quota de suspense aléatoire (target_bounces_for_ring),
                        # on cherche l'arche franche qui traversera la brèche au prochain rebond !
                        if bounces_on_current_ring >= target_bounces_for_ring:
                            best_vel, best_err, best_step, best_land_ang = predict_best_arc(
                                pos, target_speed, inward, current_gravity, current_ring, current_ball_radius)
                            if best_vel is not None:
                                vel = best_vel
                            # Si après target_bounces + 1 rebonds le trou est encore loin de l'arche,
                            # l'anneau GLISSE en douceur pendant le vol de la balle (plus aucun saut visible !)
                            if best_err >= (current_ring.gap_size / 2) * 0.80 and bounces_on_current_ring >= target_bounces_for_ring + 1:
                                pred_ring_ang = (current_ring.angle + current_ring.speed * best_step) % (2 * math.pi)
                                diff = (best_land_ang - pred_ring_ang + math.pi) % (2 * math.pi) - math.pi
                                current_ring.schedule_correction(diff, best_step - 2)

                        current_ring.hit_flash = 0.85

                        # Petite onde harmonique au point de rebond (effet goutte d'eau hypnotique)
                        impact_x = CENTER[0] + normal[0] * current_ring.radius
                        impact_y = CENTER[1] + normal[1] * current_ring.radius
                        if ENABLE_SHOCKWAVES:
                            shockwaves.append(Shockwave(impact_x, impact_y, 6, current_ring.color, max_expand=36, start_life=135.0))

                        if ENABLE_SPARKS:
                            inward_angle = math.atan2(-normal[1], -normal[0])
                            for _ in range(7):
                                particles.append(
                                    Particle(
                                        impact_x, impact_y, current_ring.color,
                                        speed_range=(2.0, 6.5), angle_center=inward_angle,
                                        angle_spread=math.pi * 0.55, is_spark=True
                                    )
                                )

                        freq = melody_freqs[note_index % len(melody_freqs)]
                        note_index += 1
                        audio.piano_note(current_time, freq=freq, duration=0.65, volume=0.36, is_chord=False, pan=pan_from_x(pos[0]))
            else:
                # Balle libérée : rebondit sur les bords de l'écran (et ne peut plus s'en échapper)
                if pos[0] - current_ball_radius < 0 or pos[0] + current_ball_radius > WIDTH:
                    vel[0] = abs(vel[0]) if pos[0] - current_ball_radius < 0 else -abs(vel[0])
                if pos[1] - current_ball_radius < 0 or pos[1] + current_ball_radius > HEIGHT:
                    vel[1] = abs(vel[1]) if pos[1] - current_ball_radius < 0 else -abs(vel[1])

            # 3. Ondes Harmoniques (Shockwaves)
            shockwaves = update_and_draw(shockwaves, draw, shake_offset)

            # 4. Traînée comète soyeuse
            num_t = len(trail_positions)
            for idx_t, (t_pos, t_col, t_rad) in enumerate(trail_positions):
                ratio = (idx_t + 1) / num_t
                r_trail = t_rad * (0.20 + 0.80 * ratio)
                alpha_trail = int(160 * (ratio ** 1.7))
                tx, ty = t_pos[0] + shake_offset[0], t_pos[1] + shake_offset[1]
                draw.ellipse([tx - r_trail, ty - r_trail, tx + r_trail, ty + r_trail], fill=(*t_col, alpha_trail))

            # 5. Anneaux
            first_active_drawn = False
            for ring in rings[ring_cursor:]:
                ring.update()
                if ring.active:
                    ring.draw(draw, shake_offset, is_innermost=(not first_active_drawn), pulse_phase=current_time)
                    first_active_drawn = True

            # 6. Éclats (Shards) et Particules
            shards = update_and_draw(shards, draw, shake_offset, current_gravity)
            particles = update_and_draw(particles, draw, shake_offset, current_gravity)

            # 7. Balle (Halo Néon + Cœur blanc)
            bx, by = pos[0] + shake_offset[0], pos[1] + shake_offset[1]
            glow_r = current_ball_radius * 1.75
            draw.ellipse([bx - glow_r, by - glow_r, bx + glow_r, by + glow_r], fill=(*ball_color, 75))
            ball_bbox = [bx - current_ball_radius, by - current_ball_radius, bx + current_ball_radius, by + current_ball_radius]
            draw.ellipse(ball_bbox, fill=(*ball_color, 255), outline=(255, 255, 255, 255), width=3)
            core_r = current_ball_radius * 0.42
            draw.ellipse([bx - core_r, by - core_r, bx + core_r, by + core_r], fill=(255, 255, 255, 220))

            # 8. Textes flottants (Combos en Anglais)
            floating_texts = update_and_draw(floating_texts, draw, shake_offset)

            # 💡 Halo néon (appliqué avant le HUD pour garder un texte net)
            if bloom:
                apply_bloom(frame_img)

            # Nombre d'anneaux APRÈS la physique de cette image (un anneau a pu casser juste au-dessus)
            rem_count = rem_now - (1 if rem_now > 0 and not rings[ring_cursor].active else 0)
            progress_hud = (NUM_RINGS - rem_count) / float(NUM_RINGS)

            # 💓 PHASE DE TENSION FINALE : battements de cœur qui accélèrent + vignette rouge pulsée
            in_tension = ENABLE_FINAL_TENSION and 0 < rem_count <= TENSION_RINGS and all_broken_frame is None
            if in_tension:
                bpm = 66 + (TENSION_RINGS - rem_count) * 14
                if next_heartbeat_time is None or current_time >= next_heartbeat_time:
                    audio.heartbeat(current_time)
                    heartbeat_flash = 1.0
                    next_heartbeat_time = current_time + 60.0 / bpm
            if heartbeat_flash > 0.02:
                for k in range(9):
                    a = int(heartbeat_flash * 70 * (1.0 - k / 9.0) ** 1.6)
                    inset = k * 14
                    draw.rectangle([inset, inset, WIDTH - inset, HEIGHT - inset], outline=(255, 30, 60, a), width=14)
                heartbeat_flash *= 0.90

            # 9. HUD 100% EN ANGLAIS POUR L'AUDIENCE INTERNATIONALE
            if ENABLE_HUD_COUNTER:
                # Titre d'accroche international (Hook) tout en haut
                draw.text((WIDTH // 2, 62), chosen_hook, font=FONT_HOOK, fill=(190, 205, 240, 215), anchor="mm")

                # Barre de progression fluide
                bar_w, bar_h = 660, 20
                bar_x = (WIDTH - bar_w) // 2
                bar_y = 165
                draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=10, fill=(26, 28, 44, 220), outline=(85, 95, 130, 170), width=2)
                if progress_hud > 0:
                    fill_w = max(20, int(bar_w * progress_hud))
                    bar_col = (*hsv_color((hue_offset + progress_hud * 0.85) % 1.0, 0.78, 1.0), 255)
                    draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=10, fill=bar_col)

                if rem_count > 0:
                    text_col = (240, 245, 255, 255) if rem_count > 5 else (255, 105, 105, 255)
                    draw.text((WIDTH // 2, 118), f"RINGS LEFT: {rem_count}", font=FONT_TITLE, fill=text_col, anchor="mm")
                    draw.text((WIDTH // 2, 208), f"HARMONY FLOW: {int(progress_hud * 100)}%", font=FONT_SUB, fill=(170, 195, 235, 195), anchor="mm")

                    # Message de suspense en bas de l'écran pendant la phase finale
                    if in_tension:
                        tension_msg = "FINAL RING..." if rem_count == 1 else f"ONLY {rem_count} LEFT..."
                        beat = 0.5 + 0.5 * heartbeat_flash
                        t_col = (255, int(120 + 80 * (1 - beat)), int(130 + 80 * (1 - beat)), int(150 + 100 * beat))
                        draw.text((WIDTH // 2, HEIGHT - 230), tension_msg, font=FONT_COMBO, fill=t_col, anchor="mm")
                else:
                    draw.text((WIDTH // 2, 118), "ALL RINGS CLEARED!", font=FONT_TITLE, fill=(110, 255, 175, 255), anchor="mm")
                    pulse_v = int(12 * math.sin(current_time * 8))
                    draw.text((WIDTH // 2, HEIGHT // 2 - 40 + pulse_v), "SATISFYING!", font=FONT_VICTORY, fill=(255, 255, 255, 245), anchor="mm")
                    draw.text((WIDTH // 2, HEIGHT // 2 + 40 + pulse_v), "FOLLOW FOR MORE", font=FONT_SUB, fill=(200, 215, 245, 220), anchor="mm")

            # 🔁 Fondu au noir début/fin -> la vidéo boucle parfaitement sur TikTok / Shorts / Reels
            if ENABLE_LOOP_FADE:
                fade_alpha = 0.0
                if current_time < FADE_IN_SECONDS:
                    fade_alpha = 1.0 - current_time / FADE_IN_SECONDS
                if all_broken_frame is not None:
                    frames_left = outro_frames_total - (frame - all_broken_frame)
                    fade_frames = FADE_OUT_SECONDS * FPS
                    if frames_left < fade_frames:
                        fade_alpha = max(fade_alpha, 1.0 - frames_left / fade_frames)
                if fade_alpha > 0.0:
                    draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(0, 0, 0, int(255 * min(1.0, fade_alpha))))

            # Envoi direct à FFmpeg par petites bandes horizontales (380 Ko au lieu de 6.2 Mo d'un coup) -> 0 MemoryError même si la RAM du PC est pleine !
            try:
                for y_band in range(0, HEIGHT, 120):
                    video_pipe.stdin.write(frame_img.crop((0, y_band, WIDTH, y_band + 120)).tobytes())
            except (BrokenPipeError, OSError):
                raise RuntimeError("FFmpeg s'est arrêté pendant l'encodage vidéo.")
            frame += 1

            if frame % (FPS * 5) == 0:
                elapsed = time.perf_counter() - render_start
                speed = (frame / FPS) / elapsed if elapsed > 0 else 0.0
                print(f"   ⏱️ {frame // FPS}s générées | Anneaux restants : {rem_count}/{NUM_RINGS} "
                      f"({int(progress_hud * 100)}%) | vitesse x{speed:.2f} temps réel")

            if all_broken_frame is not None and (frame - all_broken_frame) >= outro_frames_total:
                print(f"   ✅ Fin automatique atteinte à {frame / FPS:.2f}s ({frame} frames) !")
                break
        else:
            print(f"   ⚠️ Durée max ({max_duration}s) atteinte avant la fin de tous les anneaux.")

        video_pipe.stdin.close()
        if video_pipe.wait() != 0:
            raise RuntimeError("FFmpeg a échoué pendant l'encodage vidéo.")

        # --- MIXAGE AUDIO TRONQUÉ À LA DURÉE EXACTE ---
        actual_duration = frame / FPS
        actual_samples = min(audio.buffer.shape[1], int(actual_duration * SAMPLE_RATE))
        audio_buffer = audio.buffer[:, :actual_samples]

        print(f"2/3 - Mixage audio stéréo (nappe ambiante + réverbération) ({actual_duration:.2f}s)...")
        if ENABLE_AMBIENT_PAD:
            pad = build_ambient_pad(actual_samples, np.array(progress_curve, dtype=np.float32), pad_root)
            audio_buffer[0] += pad
            audio_buffer[1] += pad
            del pad
        if ENABLE_REVERB:
            # Délais légèrement différents à gauche/droite -> sensation d'espace très large
            audio_buffer = np.stack([apply_reverb(audio_buffer[0], 0), apply_reverb(audio_buffer[1], 23)])

        max_val = np.max(np.abs(audio_buffer))
        if max_val > 0:
            audio_buffer = audio_buffer / max_val * 0.90

        # Petit fondu de sortie audio synchronisé avec le fondu vidéo
        if ENABLE_LOOP_FADE:
            fade_n = min(actual_samples, int(FADE_OUT_SECONDS * SAMPLE_RATE))
            audio_buffer[:, actual_samples - fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)

        write_wav(temp_audio, audio_buffer)

        # --- FUSION AUDIO + VIDÉO VIA FFMPEG ---
        print("3/3 - Assemblage final MP4 (Vidéo + Audio)...")
        result = subprocess.run([
            ffmpeg_exe, "-y",
            "-i", temp_video,
            "-i", temp_audio,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            output_path
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0 or not os.path.exists(output_path):
            raise RuntimeError("FFmpeg a échoué pendant l'assemblage :\n" + result.stderr[-2000:])
        return actual_duration

    except Exception:
        # Montre la fin du journal FFmpeg pour comprendre le problème
        ffmpeg_log.flush()
        try:
            with open(ffmpeg_log_path, encoding="utf-8", errors="replace") as f:
                tail = f.read()[-1500:].strip()
            if tail:
                print("\n--- Journal FFmpeg ---\n" + tail)
        except OSError:
            pass
        raise
    finally:
        # Ferme / arrête FFmpeg et supprime TOUJOURS les fichiers temporaires (même après Ctrl+C ou une erreur)
        if video_pipe is not None and video_pipe.poll() is None:
            try:
                video_pipe.stdin.close()
            except OSError:
                pass
            video_pipe.kill()
            video_pipe.wait()
        ffmpeg_log.close()
        shutil.rmtree(work_dir, ignore_errors=True)


# ==========================================================
# 🚀 LANCEMENT
# ==========================================================
def parse_args():
    parser = argparse.ArgumentParser(description="Génère des vidéos hypnotiques de balle qui casse des anneaux.")
    parser.add_argument("--count", type=int, default=1, help="nombre de vidéos à générer d'affilée (défaut : 1)")
    parser.add_argument("--seed", type=int, default=None, help="seed précise pour refaire une vidéo à l'identique")
    parser.add_argument("--out", default=OUTPUT_DIR, help="dossier de sortie (défaut : videos/ à côté du script)")
    parser.add_argument("--draft", action="store_true", help="aperçu rapide : encodage léger et sans halo néon")
    parser.add_argument("--max-seconds", type=float, default=MAX_DURATION, help="durée max de sécurité d'une vidéo")
    parser.add_argument("--no-open", action="store_true", help="ne pas ouvrir l'explorateur à la fin")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count doit être au moins 1")
    if args.max_seconds <= 0:
        parser.error("--max-seconds doit être positif")
    return args


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    if args.seed is not None:
        first_seed = args.seed
    elif RANDOMIZE_EACH_VIDEO:
        first_seed = random.SystemRandom().randint(100000, 999999)
    else:
        first_seed = 42

    preset, crf, bloom = (("ultrafast", 26, False) if args.draft else (VIDEO_PRESET, VIDEO_CRF, ENABLE_BLOOM))
    print(f"📁 Dossier de sortie : {args.out}")

    done = []
    try:
        for n in range(args.count):
            seed = first_seed + n
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = "_draft" if args.draft else ""
            output_path = os.path.join(args.out, f"balle_hypnotique_{stamp}_seed{seed}{suffix}.mp4")
            if args.count > 1:
                print(f"\n===== Vidéo {n + 1}/{args.count} =====")
            t0 = time.perf_counter()
            duration = generate_video(seed, output_path, preset=preset, crf=crf, bloom=bloom, max_duration=args.max_seconds)
            minutes, secs = divmod(int(time.perf_counter() - t0), 60)
            print(f"\nSUCCÈS ! Vidéo de {duration:.1f}s prête (rendu en {minutes}min {secs:02d}s) :\n👉 {output_path}")
            done.append(output_path)
    except KeyboardInterrupt:
        print("\n⛔ Génération interrompue (Ctrl+C). Fichiers temporaires nettoyés.")
    except RuntimeError as e:
        print(f"\n❌ ERREUR : {e}")

    if len(done) > 1:
        print(f"\n🎬 {len(done)} vidéos générées dans {args.out}")
    if done and OPEN_FOLDER_WHEN_DONE and not args.no_open and os.name == "nt":
        subprocess.run(["explorer", f"/select,{done[-1]}"])
    return 0 if len(done) == args.count else 1


if __name__ == "__main__":
    sys.exit(main())
