"""Generator for controlled synthetic video with 4 distinct acoustic scenes.

Scenes:
1. (0-15s): Quiet engine/background ambience (120Hz low rumble, ~ -32 dBFS).
2. (15-30s): Sudden loud transient peak resembling detonation/explosion (Peak ~ -0.4 dBFS).
3. (30-45s): Alternating loud & quiet pulses resembling an action shootout/chase (High LRA, dynamic).
4. (45-60s): Near-silence (digital silence, RMS <= -70 dBFS).

Outputs: data/media/controlled_audio_test_footage_1080p.mp4
"""

import os
import subprocess
from pathlib import Path

from app.core.config import settings

ffmpeg_exe = settings.get_ffmpeg_executable()
output_dir = Path(settings.MEDIA_DIR).resolve()
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "controlled_audio_test_footage_1080p.mp4"

font_path = "/Windows/Fonts/arial.ttf"

scenes_config = [
    {
        "name": "Scene 1: Stalking Prowl (Quiet Ambience)",
        "bg_color": "#0a192f",  # Deep midnight blue
        "label": "SCENE 1: STEALTH PROWL [QUIET ENGINE AMBIENCE]",
        "sub": "Cruising down alleyways at low RPM. Muted engine tone (~ -32 dBFS).",
        "audio_filter": "sine=frequency=120:sample_rate=48000:duration=15,volume=0.04",
        "audio_type": "lavfi_sine",
        "indicator": ">> [LOW-RUMBLE AMBIENCE: -32 dBFS] >>>",
        "accent_color": "cyan",
    },
    {
        "name": "Scene 2: Bank Vault Breach (Explosion Peak)",
        "bg_color": "#590d22",  # Deep crimson red
        "label": "SCENE 2: VAULT DETONATION [SUDDEN LOUD TRANSIENT PEAK]",
        "sub": "Breaching charge detonated at 7s! Explosive burst peaking near 0 dBFS.",
        "audio_expr": r"if(between(t\,7.0\,7.5)\,0.95*sin(2*PI*280*t)+0.8*sin(2*PI*90*t)\,0.01*sin(2*PI*120*t))",
        "audio_type": "aevalsrc",
        "indicator": "!!! [HIGH TRANSIENT DETONATION PEAK: -0.5 dBFS] !!!",
        "accent_color": "red",
    },
    {
        "name": "Scene 3: Downtown Shootout (Dynamic Alternating)",
        "bg_color": "#1b4332",  # Dark emerald green
        "label": "SCENE 3: INTERSECTION SHOOTOUT [ALTERNATING LOUD & QUIET]",
        "sub": "Rapid bursts alternating with tactical cover. Dynamic range & silence gaps.",
        "audio_expr": r"if(mod(floor(t/1.5)\,2)\,0.85*sin(2*PI*440*t)\,0.005*sin(2*PI*440*t))",
        "audio_type": "aevalsrc",
        "indicator": "### [DYNAMIC COMBAT PULSES: LRA > 8 LU] ###",
        "accent_color": "yellow",
    },
    {
        "name": "Scene 4: Stealth Rooftop Escape (Near-Silence)",
        "bg_color": "#101018",  # Near-black charcoal
        "label": "SCENE 4: ESCAPE ROOFTOP [DEAD SILENCE & SUSPENSE]",
        "sub": "Footsteps on rubber matting. Complete silence (< -70 dBFS).",
        "audio_filter": "anullsrc=r=48000:cl=stereo:d=15",
        "audio_type": "lavfi_null",
        "indicator": "... [NEAR-ZERO ACOUSTIC ENERGY: SILENCE] ...",
        "accent_color": "gray",
    },
]

temp_dir = output_dir / "temp_controlled_segments"
temp_dir.mkdir(parents=True, exist_ok=True)

segment_files = []
for idx, sc in enumerate(scenes_config, 1):
    seg_file = temp_dir / f"controlled_seg_{idx}.mp4"
    segment_files.append(seg_file)

    clean_sub = sc["sub"].replace("'", "").replace(":", "")
    clean_label = sc["label"].replace("'", "").replace(":", "")
    clean_ind = sc["indicator"].replace("'", "").replace(":", "")

    vf_chain = [
        "drawbox=y=0:h=90:color=black@0.85:t=fill",
        f"drawtext=fontfile={font_path}:text='SYNTHETIC_TEST_ONLY -- NOT REAL GAMEPLAY':fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=25",
        "drawbox=y=h-120:h=120:color=black@0.85:t=fill",
        f"drawtext=fontfile={font_path}:text='{clean_label}':fontcolor=white:fontsize=32:x=(w-text_w)/2:y=120",
        f"drawtext=fontfile={font_path}:text='Timecode\\: %{{pts\\:hms}} | 1920x1080 @ 30FPS | VANTYX AUDIO LAB':fontcolor=0x00FFCC:fontsize=24:x=(w-text_w)/2:y=170",
        "drawbox=x=100:y=350:w=1720:h=380:color=black@0.4:t=fill",
        f"drawtext=fontfile={font_path}:text='{clean_ind}':fontcolor={sc['accent_color']}:fontsize=36:x=mod(t*220\\,w):y=480",
        f"drawtext=fontfile={font_path}:text='CONTROLLED ACOUSTIC TEST BENCH':fontcolor=white:fontsize=26:x=(w-text_w)/2:y=560",
        f"drawtext=fontfile={font_path}:text='{clean_sub}':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=h-75",
    ]
    vf = ",".join(vf_chain)

    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", f"color=c={sc['bg_color']}:s=1920x1080:r=30:d=15",
    ]

    if sc["audio_type"] == "aevalsrc":
        cmd.extend(["-f", "lavfi", "-i", f"aevalsrc='{sc['audio_expr']}':s=48000:d=15"])
    elif sc["audio_type"] == "lavfi_sine":
        cmd.extend(["-f", "lavfi", "-i", sc["audio_filter"]])
    elif sc["audio_type"] == "lavfi_null":
        cmd.extend(["-f", "lavfi", "-i", sc["audio_filter"]])

    cmd.extend([
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(seg_file),
    ])

    print(f"Generating Controlled Segment {idx}: {sc['name']}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error generating segment {idx}:", res.stderr)
        raise RuntimeError(f"FFmpeg error: {res.stderr}")

print("Concatenating 4 controlled segments into final video...")
concat_inputs = []
filter_inputs = ""
for i, sf in enumerate(segment_files):
    concat_inputs.extend(["-i", str(sf)])
    filter_inputs += f"[{i}:v][{i}:a]"

filter_complex = f"{filter_inputs}concat=n=4:v=1:a=1[outv][outa]"

concat_cmd = [
    ffmpeg_exe, "-y",
    *concat_inputs,
    "-filter_complex", filter_complex,
    "-map", "[outv]",
    "-map", "[outa]",
    "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    str(output_path),
]

res_cat = subprocess.run(concat_cmd, capture_output=True, text=True)
if res_cat.returncode != 0:
    print("Error concatenating:", res_cat.stderr)
    raise RuntimeError(f"FFmpeg concat error: {res_cat.stderr}")

print(f"SUCCESS: Generated controlled audio synthetic video at {output_path}")
print(f"File Size: {os.path.getsize(output_path):,} bytes")
