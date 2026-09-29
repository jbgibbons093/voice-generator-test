"""Create a browser playback copy; preserve the original recording and all pauses."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([
    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
    '-i', str(ROOT / 'archive' / 'portal-insulin-original.mp4'),
    '-i', str(ROOT / 'media' / 'narration-original.mp3'),
    '-map', '0:v:0', '-map', '1:a:0',
    '-c:v', 'copy', '-c:a', 'aac', '-profile:a', 'aac_low', '-b:a', '192k',
    '-movflags', '+faststart', '-disposition:a:0', 'default',
    str(ROOT / 'media' / 'portal-insulin-study.mp4'),
], check=True)
