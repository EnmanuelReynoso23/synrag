"""Banda sonora original del video, sintetizada con numpy (sin muestras ni música de terceros).

    python video/musica.py musica.wav

La mayor parte va en La menor, 100 BPM, con la progresión Am - F - C - G (2 compases cada acorde). Las capas entran
con las escenas de escenas.html y hay efectos sincronizados: tecleo en las terminales, barridos en los
cambios de escena y un golpe grave cuando aparece el -63,9 %. Si cambian los tiempos de escenas.html, se cambian aquí.
"""
import sys
import wave

import numpy as np

SR = 48000
DURACION = 68.0
BPM = 100
PULSO = 60 / BPM
COMPAS = 4 * PULSO

# Cambios de escena (data-desde de escenas.html)
ESCENAS = [0, 5.6, 12.4, 20.6, 33, 40.4, 49.6, 55.6, 61.2]
# Comandos tecleados: (inicio absoluto, caracteres, caracteres por segundo), igual que GUIONES en escenas.html
TECLEO = [(20.6 + 0.9, len("SYNRAG index"), 22),
          (20.6 + 3.2, len('SYNRAG --project flask "SecureCookieSessionInterface open_session"'), 34),
          (33 + 0.9, len("SYNRAG impact HTTPException"), 24)]
GOLPE = 40.4 + 0.5  # aparece el -63,9 %

# Acordes: (bajo, notas del colchón) en MIDI
ACORDES = [(45, (57, 60, 64)), (41, (57, 60, 65)), (48, (55, 60, 64)), (43, (55, 59, 62))]

N = int(DURACION * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(23)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def filtrar(x, bajo=None, alto=None):
    """Filtro suave en frecuencia (paso bajo en `alto`, paso alto en `bajo`)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if alto:
        g /= np.sqrt(1 + (f / alto) ** 4)
    if bajo:
        g *= (f / bajo) ** 2 / np.sqrt(1 + (f / bajo) ** 4)
    return np.fft.irfft(X * g, len(x))


def tramo(a, b, sube=0.0, baja=0.0):
    """Envolvente de 0 a 1 entre a y b, con rampas de entrada y salida."""
    e = ((t >= a) & (t < b)).astype(float)
    if sube:
        e = np.where((t >= a) & (t < a + sube), (t - a) / sube, e)
    if baja:
        e = np.where((t >= b - baja) & (t < b), (b - t) / baja, e)
    return e


def sierra_suave(f, fase=0.0, armonicos=7):
    return sum(np.sin(2 * np.pi * f * k * t + fase * k) / k for k in range(1, armonicos + 1))


def reverb(x, segundos=1.8):
    n = int(segundos * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = filtrar(ir, alto=5000)
    m = len(x) + n
    y = np.fft.irfft(np.fft.rfft(x, m) * np.fft.rfft(ir, m), m)[: len(x)]
    return y / (np.abs(y).max() + 1e-9) * np.abs(x).max()


def cola(tt, largo):
    """Desvanece los últimos 15 ms de una nota para que no haga clic al cortarse."""
    return np.clip((largo - tt) / 0.015, 0, 1)


def acorde_en(seg):
    return ACORDES[int(seg // (2 * COMPAS)) % len(ACORDES)]


# --- Colchón (pad): sierras desafinadas y filtradas, estéreo ---------------------------------
pad_l, pad_r = np.zeros(N), np.zeros(N)
paso = 2 * COMPAS
for i in range(int(np.ceil(DURACION / paso)) + 1):
    a = i * paso
    _, notas = ACORDES[i % len(ACORDES)]
    env = tramo(a - 0.4, a + paso + 0.6, sube=0.9, baja=1.0)
    if not env.any():
        continue
    for nota in notas:
        f = hz(nota)
        pad_l += env * sierra_suave(f * 0.997, 0.3)
        pad_r += env * sierra_suave(f * 1.003, 1.1)
pad_l, pad_r = filtrar(pad_l, bajo=90, alto=1400), filtrar(pad_r, bajo=90, alto=1400)

# --- Bajo con pulso de corcheas -------------------------------------------------------------
bajo = np.zeros(N)
corchea = PULSO / 2
for k in range(int(DURACION / corchea)):
    a = k * corchea
    f = hz(acorde_en(a)[0])
    i0, i1 = int(a * SR), min(N, int((a + corchea) * SR))
    tt = t[i0:i1] - a
    bajo[i0:i1] += np.sin(2 * np.pi * f * tt) * np.exp(-tt * 5) * (1 - np.exp(-tt * 400)) * cola(tt, corchea)
bajo = filtrar(bajo, alto=400)

# --- Arpegio (corcheas, tono suave tipo pluck) -----------------------------------------------
arp_l, arp_r = np.zeros(N), np.zeros(N)
patron = [0, 1, 2, 1, 0, 2, 1, 2]
for k in range(int(DURACION / corchea)):
    a = k * corchea
    _, notas = acorde_en(a)
    nota = notas[patron[k % len(patron)]] + 12 + (12 if k % 8 == 7 else 0)
    f = hz(nota)
    i0, i1 = int(a * SR), min(N, int((a + 0.9) * SR))
    tt = t[i0:i1] - a
    s = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 7) * (1 - np.exp(-tt * 600)) * cola(tt, 0.9)
    pan = 0.35 if k % 2 else -0.35
    arp_l[i0:i1] += s * (1 - pan)
    arp_r[i0:i1] += s * (1 + pan)

# --- Batería suave ----------------------------------------------------------------------------
bombo, plato = np.zeros(N), np.zeros(N)
lado = np.ones(N)  # "sidechain": el colchón y el bajo bajan un poco en cada bombo
for k in range(int(DURACION / PULSO)):
    a = k * PULSO
    i0, i1 = int(a * SR), min(N, int((a + 0.5) * SR))
    tt = t[i0:i1] - a
    fase = 2 * np.pi * (45 * tt + (110 - 45) / 18 * (1 - np.exp(-tt * 18)))
    bombo[i0:i1] += np.sin(fase) * np.exp(-tt * 7) * cola(tt, 0.5)
    lado[i0:i1] = np.minimum(lado[i0:i1], 1 - 0.45 * np.exp(-tt * 8))
    j0, j1 = int((a + corchea) * SR), min(N, int((a + corchea + 0.08) * SR))
    plato[j0:j1] += rng.standard_normal(j1 - j0) * np.exp(-(t[j0:j1] - a - corchea) * 60)
plato = filtrar(plato, bajo=7000)

# --- Efectos sincronizados -------------------------------------------------------------------
fx = np.zeros(N)
for inicio, chars, cps in TECLEO:  # una tecla por carácter, con volumen y tono algo distintos
    for c in range(chars):
        a = inicio + c / cps + rng.uniform(-0.008, 0.008)
        i0, i1 = int(a * SR), min(N, int((a + 0.025) * SR))
        tt = t[i0:i1] - a
        fx[i0:i1] += rng.standard_normal(i1 - i0) * np.exp(-tt * 260) * rng.uniform(0.5, 1.0) * 0.55
fx = filtrar(fx, bajo=1800, alto=7000)

barrido = np.zeros(N)
for e in ESCENAS[1:]:  # ruido que sube y se apaga en cada cambio de escena
    env = np.where((t > e - 0.7) & (t <= e), ((t - e + 0.7) / 0.7) ** 2, 0)
    env += np.where((t > e) & (t < e + 0.5), np.exp(-(t - e) * 9), 0)
    barrido += env * rng.standard_normal(N)
barrido = filtrar(barrido, bajo=500, alto=3500) * 0.22

golpe = np.zeros(N)
i0 = int(GOLPE * SR)
tt = t[i0:] - GOLPE
golpe[i0:] = np.sin(2 * np.pi * (38 * tt + 60 / 6 * (1 - np.exp(-tt * 6)))) * np.exp(-tt * 2.2)
brillo = filtrar(rng.standard_normal(N), bajo=4000) * np.where(t >= GOLPE, np.exp(-(t - GOLPE) * 3.5), 0) * 0.25

# --- Arreglo por escenas ---------------------------------------------------------------------
v_pad = 0.55 * tramo(0, DURACION, sube=2.5, baja=3.5)
v_bajo = 0.55 * tramo(5.6, 63.5, sube=1.2, baja=2.0)
v_arp = 0.16 * tramo(12.4, DURACION, sube=2.0, baja=4.0)
v_drums = tramo(20.6, 61.2, sube=0.05, baja=0.8)
v_demo = 1 - 0.25 * tramo(20.6, 40.4, sube=0.5, baja=0.5)  # la música baja un poco bajo el tecleo
lado = np.where(v_drums > 0, lado, 1)

mezcla_l = (pad_l * v_pad * lado + bajo * v_bajo * lado) * v_demo + arp_l * v_arp * v_demo
mezcla_r = (pad_r * v_pad * lado + bajo * v_bajo * lado) * v_demo + arp_r * v_arp * v_demo

# normalizar cada capa antes de mezclar para que los volúmenes de arriba signifiquen algo
def norm(x):
    return x / (np.abs(x).max() + 1e-9)

mezcla_l, mezcla_r = norm(mezcla_l), norm(mezcla_r)
eco_l, eco_r = reverb(mezcla_l), reverb(mezcla_r)
comun = (norm(bombo) * 0.55 * v_drums + norm(plato) * 0.12 * v_drums + norm(fx) * 0.35
         + norm(barrido) * 0.3 + norm(golpe) * 0.8 + norm(brillo) * 0.15)
L = mezcla_l * 0.75 + eco_l * 0.3 + comun
R = mezcla_r * 0.75 + eco_r * 0.3 + comun

final = np.stack([L, R], axis=1)
final = np.tanh(final / np.abs(final).max() * 1.2) / np.tanh(1.2)
final *= 10 ** (-1 / 20)  # pico a -1 dBFS; ffmpeg loudnorm deja el volumen final

with wave.open(sys.argv[1] if len(sys.argv) > 1 else "musica.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((final * 32767).astype("<i2").tobytes())
