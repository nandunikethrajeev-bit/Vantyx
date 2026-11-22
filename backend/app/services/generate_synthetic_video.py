"""Script to generate a 60-second, 1080p, 30fps synthetic test video with 4 distinct scenes."""

import os
import subprocess
from pathlib import Path
from app.core.config import settings

ffmpeg_exe = settings.get_ffmpeg_executable()
output_dir = Path(settings.MEDIA_DIR).resolve()
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / "synthetic_test_footage_1080p.mp4"

font_path = "/Windows/Fonts/arial.ttf"

scenes_config = [
    {
        "name": "Scene 1: Vice City Highway Chase",
        "bg_color": "#0d1b2a",
        "label": "SCENE 1: HIGH-SPEED PURSUIT [HEIST ESCAPE]",
        "sub": "Suspect vehicle fleeing northbound on Ocean Drive at 120 MPH!",
        "tone_freq": 440,
        "indicator": ">> [PURSUIT VEHICLE IN TRANSIT] >>>",
        "accent_color": "red",
    },
    {
        "name": "Scene 2: Sunset Boulevard Escape",
        "bg_color": "#4a0e17",
        "label": "SCENE 2: SUNSET BOULEVARD ESCAPE [PACING / DRIVING]",
        "sub": "Switching to off-road cruiser. Marina dock rendezvous in 2 minutes.",
        "tone_freq": 554,
        "indicator": "=== [TACTICAL POSITIONING: DOCKS] ===",
        "accent_color": "yellow",
    },
    {
        "name": "Scene 3: Downtown Vault Infiltration",
        "bg_color": "#081c15",
        "label": "SCENE 3: FIRST NATIONAL VAULT INFILTRATION [HIGH STAKES]",
        "sub": "Thermal charge active. Vault door opening in 5... 4... 3...",
        "tone_freq": 659,
        "indicator": "## [INFILTRATION / HEIST IN PROGRESS] ##",
        "accent_color": "green",
    },
    {
        "name": "Scene 4: Airport Runway Getaway Finale",
        "bg_color": "#240046",
        "label": "SCENE 4: RUNWAY TAKEOFF FINALE [CLIMAX & ESCAPE]",
        "sub": "Cargo plane airborne. Evaded all 5-star heat. Mission Passed!",
        "tone_freq": 880,
        "indicator": "<<< [MISSION COMPLETE: AIRBORNE ESCAPE] <<<",
        "accent_color": "cyan",
    },
]

temp_dir = output_dir / "temp_segments"
temp_dir.mkdir(parents=True, exist_ok=True)

segment_files = []
for idx, sc in enumerate(scenes_config, 1):
    seg_file = temp_dir / f"seg_{idx}.mp4"
    segment_files.append(seg_file)
    
    clean_sub = sc['sub'].replace("'", "").replace(":", "")
    clean_label = sc['label'].replace("'", "").replace(":", "")
    clean_ind = sc['indicator'].replace("'", "").replace(":", "")
    
    vf_chain = [
        "drawbox=y=0:h=90:color=black@0.85:t=fill",
        f"drawtext=fontfile={font_path}:text='SYNTHETIC_TEST_ONLY -- NOT REAL GAMEPLAY':fontcolor=yellow:fontsize=36:x=(w-text_w)/2:y=25",
        "drawbox=y=h-120:h=120:color=black@0.85:t=fill",
        f"drawtext=fontfile={font_path}:text='{clean_label}':fontcolor=white:fontsize=34:x=(w-text_w)/2:y=120",
        f"drawtext=fontfile={font_path}:text='Timecode\\: %{{pts\\:hms}} | 1920x1080 @ 30FPS | VANTYX TEST LAB':fontcolor=0x00FFCC:fontsize=26:x=(w-text_w)/2:y=170",
        f"drawbox=x=100:y=350:w=1720:h=380:color=black@0.4:t=fill",
        f"drawtext=fontfile={font_path}:text='{clean_ind}':fontcolor={sc['accent_color']}:fontsize=38:x=mod(t*220\\,w):y=480",
        f"drawtext=fontfile={font_path}:text='SIMULATED ACTION MOTION':fontcolor=white:fontsize=28:x=(w-text_w)/2:y=560",
        f"drawtext=fontfile={font_path}:text='{clean_sub}':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=h-75",
    ]
    vf = ",".join(vf_chain)
    
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "lavfi", "-i", f"color=c={sc['bg_color']}:s=1920x1080:r=30:d=15",
        "-f", "lavfi", "-i", f"sine=frequency={sc['tone_freq']}:sample_rate=48000:duration=15",
        "-vf", vf,
        "-af", "volume=0.15,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        str(seg_file)
    ]
    print(f"Generating Segment {idx}: {sc['name']}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error generating segment {idx}:", res.stderr)
        raise RuntimeError(f"FFmpeg error: {res.stderr}")

print("Concatenating 4 segments into final synthetic test footage...")
concat_inputs = []
filter_inputs = ""
for i, sf in enumerate(segment_files):
    concat_inputs.extend(["-i", str(sf)])
    filter_inputs += f"[{i}:v][{i}:a]"

filter_complex = f"{filter_inputs}concat=n=4:v=1:a=1[v][a]"

cmd_concat = [
    ffmpeg_exe, "-y",
    *concat_inputs,
    "-filter_complex", filter_complex,
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k",
    "-metadata", "title=SYNTHETIC_TEST_ONLY — NOT REAL GAMEPLAY",
    "-metadata", "comment=VANTYX Pipeline Synthetic Test Video",
    "-metadata", "artist=VANTYX Synthetic Pipeline Generator",
    str(output_path)
]

res = subprocess.run(cmd_concat, capture_output=True, text=True)
if res.returncode != 0:
    print("Concat error:", res.stderr)
    raise RuntimeError(f"Concat error: {res.stderr}")

print(f"SUCCESS: Generated synthetic test video at: {output_path}")
print(f"File size: {os.path.getsize(output_path):,} bytes")

for sf in segment_files:
    try:
        sf.unlink()
    except Exception:
        pass
try:
    temp_dir.rmdir()
except Exception:
    pass
