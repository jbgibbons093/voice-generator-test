# voice-generator-test

PORTAL research videos with public viewing pages. The main page presents *Patient Out-of-Pocket Spending on Generic and Brand-Name Prescription Drugs*. The Medicare insulin cap video remains available at `insulin.html`.

**Watch:** https://jbgibbons093.github.io/voice-generator-test/

**New paper:** Cai CL, Kesselheim AS, Rome BN. Patient Out-of-Pocket Spending on Generic and Brand-Name Prescription Drugs. JAMA Network Open. 2026;9(9):e2633401. https://doi.org/10.1001/jamanetworkopen.2026.33401

## Generic and brand-name medicines

The 55.327-second supplied narration retains every word and pause at its original speed. Thirteen animated scenes use an indigo, periwinkle, and coral palette and the official PORTAL logo. Findings and policy options follow the paper.

- `index.html` is the main viewing page, with a sound-enabled play button and a link to the earlier video.
- `media/portal-generic-spending.mp4` is the 1080p H.264/AAC-LC sharing version.
- `media/generic-spending-narration-original.mp3` is the byte-identical supplied recording.
- `archive/portal-generic-spending-original-audio.mp4` preserves the exact original MP3 audio stream. Both encoded audio packets and decoded samples were verified against the source.
- `generic-spending/` contains the approved narration, scene timing, and SRT/WebVTT captions.
- `src/render_generic.py` recreates the animation in `build/generic-spending/`. Run with `--preview` to generate stills.
- `checks/generic-spending-media-verification.json` records the export checks. Browser verification measures decoded audio during playback.

The AAC version preserves the performance through a codec conversion. Its decoded audio correlates 0.99997 with the supplied recording at zero lag. The exact MP3 audio is available in the original-audio master and standalone recording.

## Medicare insulin cap video

**Watch the earlier video:** https://jbgibbons093.github.io/voice-generator-test/insulin.html

**Paper:** Hong et al. JAMA Internal Medicine. 2026;186(6):723–731. https://doi.org/10.1001/jamainternmed.2026.0255

## Audio playback

The original export carried MP3 audio inside an MP4 container. Some viewers reported silent playback. The viewing copy pairs the unchanged H.264 video with AAC-LC audio for broader browser compatibility. Playback starts from a user click, with sound enabled, rather than relying on autoplay.

The performance is unchanged: no pauses, words, or breaths were removed; no time stretching, volume normalization, music, or sound effects were added. The AAC copy is a codec conversion, so its compressed bytes differ. The original recording remains available byte-for-byte in `media/narration-original.mp3`, and the previous export remains in `archive/portal-insulin-original.mp4`.

The full recording is 47.647 seconds; the video is approximately 47.67 seconds at 30 frames per second. Scene changes follow the words in the supplied recording. The opening frame includes all twelve authors. The final narration does not include a comparison-group sentence; the observational limitation remains in the on-screen text.

## Contents

- `insulin.html` is the insulin viewing page. Both viewing pages share `styles.css` and `player.js`.
- `media/portal-insulin-study.mp4`: browser playback and sharing copy, H.264/AAC-LC, 1080p.
- `media/narration-original.mp3`: unmodified supplied narration.
- `archive/portal-insulin-original.mp4`: previous export with the unmodified MP3 audio stream.
- `script.txt`, `timed-script.txt`, `timeline.json`: narration and scene timing.
- `captions.srt`, `captions.vtt`: optional captions; captions are also visible in the animation.
- `src/render_portal.py`: animation source. Output is written to `build/`.
- `src/package_playback.py`: creates the compatible video without editorial audio changes.
- `checks/`: media and browser verification tools and results.

## Local preview

Run `python -m http.server 8080` from the repository, then open http://localhost:8080. No API key, account, or build step is required to view the page.

To rebuild the compatibility copy, install FFmpeg on your PATH and run `python src/package_playback.py`.

To re-render the animation, install `requirements.txt`, FFmpeg, Cairo, and the Windows Georgia and Segoe UI fonts. Run `python src/render_portal.py`; use `--preview` to produce still previews only. This recreates the original-audio export in `build/`.

## Source and branding

The paper's title, author list, findings, and study limitations informed the animation. Costs are quarterly spending among insulin users, and A1c changes are percentage points. Illustrative people, coins, and policy tiles are not additional study data.

PORTAL logo assets come from [PORTAL's website](https://portalresearch.org/about-portal/); source URLs are recorded in `assets/source.txt`. Logos and narration remain the property of their respective rights holders. The page is a study summary, not an official journal production. No voice generation service or credentials are included.
