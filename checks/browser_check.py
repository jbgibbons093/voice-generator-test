"""Exercise user-initiated playback and measure actual decoded browser audio."""
from pathlib import Path
import argparse, json
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--output', default='checks/local-browser.json')
args = parser.parse_args()
results = []
with sync_playwright() as p:
    for name in ['chromium', 'firefox', 'webkit']:
        print('Checking ' + name, flush=True)
        browser = None
        try:
            browser = getattr(p, name).launch(headless=True)
            page = browser.new_page(viewport={'width': 1365, 'height': 1080})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.url, wait_until='domcontentloaded', timeout=45000)
            page.wait_for_function('document.querySelector("video").readyState >= 2', timeout=20000)
            meter_available = page.evaluate('Boolean(window.AudioContext || window.webkitAudioContext)')
            if meter_available:
                page.evaluate('''() => {
                const v = document.querySelector('video');
                window.qaContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = qaContext.createMediaElementSource(v);
                window.qaAnalyser = qaContext.createAnalyser();
                qaAnalyser.fftSize = 2048;
                source.connect(qaAnalyser); qaAnalyser.connect(qaContext.destination);
            }''')
            page.get_by_role('button', name='Play with sound').click()
            if meter_available:
                page.evaluate('qaContext.resume()')
            audio = page.evaluate('''async () => {
                const v = document.querySelector('video'), a = new Float32Array(2048);
                let rmsMax = 0, audibleSamples = 0;
                for (let k = 0; k < 40; k++) {
                    await new Promise(resolve => setTimeout(resolve, 75));
                    if (window.qaAnalyser) qaAnalyser.getFloatTimeDomainData(a);
                    const rms = Math.sqrt(a.reduce((s, x) => s + x*x, 0) / a.length);
                    rmsMax = Math.max(rmsMax, rms);
                    if (rms > 0.003) audibleSamples++;
                }
                return {rmsMax, audibleSamples, time: v.currentTime, muted: v.muted,
                    volume: v.volume, paused: v.paused, context: window.qaContext?.state ?? 'unavailable',
                    error: v.error && {code: v.error.code, message: v.error.message}};
            }''')
            if meter_available:
                assert audio['rmsMax'] > .005 and audio['audibleSamples'] > 8, audio
            assert audio['time'] > 2 and not audio['muted'] and not audio['paused'], audio
            assert audio['volume'] > 0 and not audio['error'], audio
            assert not errors, errors
            page.locator('video').evaluate('(v) => v.pause()')
            if name == 'chromium':
                page.screenshot(path='checks/local-desktop.png', full_page=True)
                page.set_viewport_size({'width': 390, 'height': 844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path='checks/local-mobile.png', full_page=True)
            results.append({'engine': name, 'version': browser.version, 'passed': True,
                            'decoded_audio_verified': meter_available,
                            'scope': 'decoded audio and playback' if meter_available else 'playback only; this Windows WebKit build has no Web Audio API',
                            'audio': audio})
        except Exception as exc:
            results.append({'engine': name, 'passed': False, 'error': str(exc)})
        finally:
            if browser:
                browser.close()
Path(args.output).write_text(json.dumps({'url': args.url, 'results': results}, indent=2))
print(json.dumps(results, indent=2))
assert all(x['passed'] for x in results), 'One or more browser checks failed'
