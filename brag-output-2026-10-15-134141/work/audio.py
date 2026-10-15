import numpy as np, wave
from render import SCENES, CHAT, DUR

SR = 44100
N = int(SR * DUR)
tt = np.arange(N) / SR


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= N:
        return
    j = min(N, i + len(sig))
    buf[i:j] += sig[:j - i] * gain


def pluck(m, dur=0.9, d=0.2, bright=0.3):
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = hz(m)
    s = np.sin(2 * np.pi * f * t) + bright * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.06)
    return s * np.minimum(t / 0.004, 1) * np.exp(-t / d)


# one chord per scene, cycling Am F C G; the outro lifts to Cadd9
PROG = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62])]
chords = []
for i, (a, b, kind, key) in enumerate(SCENES):
    if kind == 'outro':
        chords.append((a, b, 48, [55, 60, 64, 67]))
    else:
        chords.append((a, b) + PROG[i % 4])

music = np.zeros(N)
BEAT = 0.5  # 120 bpm
for (a, b, bass, tones) in chords:
    L = b - a + 0.8
    n = int(SR * L)
    t = np.arange(n) / SR
    e = np.minimum(t / 0.5, 1) * np.clip((L - t) / 0.8, 0, 1)
    pad = np.zeros(n)
    for m in tones:
        for det in (-0.08, 0.08):
            f = hz(m) * 2 ** (det / 12)
            pad += np.sin(2 * np.pi * f * t) + 0.2 * np.sin(2 * np.pi * 2 * f * t + 0.3)
    pad *= 0.5 + 0.5 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t))
    add(music, a, pad * e * 0.03)
    k = 0
    while a + k * BEAT < b:
        st = a + k * BEAT
        if st >= 0.6:
            add(music, st, pluck(bass - 12 if bass > 40 else bass, 0.5, 0.18, 0.05), 0.16 if k % 2 == 0 else 0.09)
        k += 1
    steps = [0, 1, 2, 1, 2, 1, 0, 2]
    k = 0
    while a + k * BEAT / 2 < b:
        st = a + k * BEAT / 2
        if 1.2 <= st < DUR - 1.2:
            m = tones[steps[k % 8] % len(tones)] + 12
            add(music, st, pluck(m, 0.6, 0.12, 0.2), 0.035 if k % 2 else 0.05)
        k += 1

noise = np.random.default_rng(7).standard_normal(int(0.05 * SR))
hat = np.diff(noise, prepend=0) * np.exp(-np.arange(len(noise)) / (0.012 * SR))
chat_start = SCENES[1][0]
chat_end = SCENES[-1][0]
t0 = chat_start
while t0 < chat_end:
    add(music, t0 + BEAT / 2, hat, 0.012)
    t0 += BEAT

sfx = np.zeros(N)
for k in range(26):
    add(sfx, 0.75 + k * 0.05, pluck(93 + 6 * (k % 3), 0.03, 0.006, 0.0), 0.03)
add(sfx, 2.15, pluck(81, 0.7, 0.16), 0.06)  # send

# message pops follow the chat timeline: user E5, agent A5, system note soft C5
for (a, b, kind, key) in SCENES:
    if kind != 'chat':
        continue
    for m in CHAT[key][0]:
        ta, k = m[0], m[1]
        if k == 'user':
            add(sfx, a + ta, pluck(76, 0.7, 0.14), 0.045)
        elif k == 'sys':
            add(sfx, a + ta, pluck(72, 0.9, 0.25), 0.04)
        else:
            add(sfx, a + ta, pluck(81, 0.7, 0.16), 0.045)
    if key == 'intake':  # "saved": rising A-C-E
        for i, m in enumerate([81, 84, 88]):
            add(sfx, a + 3.7 + i * 0.07, pluck(m, 0.8, 0.2), 0.035)

oa = SCENES[-1][0]
for i, m in enumerate([72, 74, 76, 79, 81, 84, 88]):
    add(sfx, oa + 0.6 + i * 0.09, pluck(m, 0.7, 0.16), 0.028)

mix = music + sfx
wet = np.zeros(N)
for dly, g in [(0.043, 0.3), (0.071, 0.26), (0.113, 0.22), (0.167, 0.17), (0.241, 0.12), (0.331, 0.08)]:
    k = int(dly * SR)
    wet[k:] += mix[:-k] * g
mix = mix + wet * 0.5
k = 5
mix = np.convolve(mix, np.ones(k) / k, mode='same')
mix *= np.minimum(tt / 0.4, 1) * np.clip((DUR - tt) / 1.6, 0, 1)
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.2) / np.tanh(1.2) * 0.72
L = mix
R = np.roll(mix, int(0.009 * SR))
pcm = (np.stack([L, R], 1) * 32767).astype('<i2')
with wave.open('music.wav', 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
