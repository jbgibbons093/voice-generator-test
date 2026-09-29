"""Check streams, decoded speech timing, and the original recording's pauses."""
from pathlib import Path
import hashlib, json, subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'media'/'narration-original.mp3'
original = ROOT/'archive'/'portal-insulin-original.mp4'
playback = ROOT/'media'/'portal-insulin-study.mp4'

def call(args):
    return subprocess.check_output(args)
def decoded(path):
    return np.frombuffer(call(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-f','f32le','-']),dtype='<f4')
def stream_hash(path, stream, codec):
    return call(['ffmpeg','-v','error','-i',str(path),'-map',stream,'-c',codec,'-f','hash','-hash','sha256','-']).decode().strip()

a, archived, b = decoded(source), decoded(original), decoded(playback)
assert np.array_equal(a, archived), 'Archived audio differs from the supplied recording'
assert stream_hash(original,'0:v:0','copy') == stream_hash(playback,'0:v:0','copy'), 'Video frames changed'
n = min(len(a),len(b))
correlation = float(np.corrcoef(a[:n],b[:n])[0,1])
gain = float(np.dot(a[:n],b[:n])/np.dot(a[:n],a[:n]))
assert correlation > .995, correlation
assert abs(gain-1) < .01, gain
pauses=[]
for start,end in [(4.85,5.14),(15.95,16.60),(34.25,34.89),(43.95,44.50)]:
    x,y=a[round(start*44100):round(end*44100)],b[round(start*44100):round(end*44100)]
    levels=[float(20*np.log10(max(1e-12,np.sqrt(np.mean(z*z))))) for z in (x,y)]
    assert max(levels)<-40, levels
    pauses.append({'start':start,'end':end,'original_dbfs':levels[0],'playback_dbfs':levels[1]})
meta=json.loads(call(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_type,codec_name,profile,sample_rate,channels,duration,width,height,nb_frames','-of','json',str(playback)]))
assert [s['codec_name'] for s in meta['streams']]==['h264','aac']
subprocess.run(['ffmpeg','-v','error','-i',str(playback),'-f','null','-'],check=True)
report={'original_file_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'archived_audio_bit_exact':True,'video_stream_unchanged':True,
        'decoded_audio_correlation_at_zero_lag':correlation,'linear_gain_ratio':gain,
        'original_duration':len(a)/44100,'pauses':pauses,'playback_media':meta,'full_decode':'passed'}
(ROOT/'checks'/'media-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
