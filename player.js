"use strict";

const video = document.getElementById("study-video");
const original = document.getElementById("original-audio");
const playButton = document.getElementById("play-sound");
const status = document.getElementById("playback-status");

playButton.addEventListener("click", async () => {
  original.pause();
  video.muted = false;
  if (video.volume === 0) video.volume = 1;
  if (video.ended) video.currentTime = 0;
  try {
    await video.play();
    status.textContent = "Playing with sound.";
  } catch {
    status.textContent = "Use the video’s play button, or download the video to watch it on your device.";
  }
});

video.addEventListener("play", () => {
  original.pause();
  status.textContent = video.muted || video.volume === 0 ? "The player is muted. Click Play with sound to unmute." : "Playing with sound.";
});
video.addEventListener("volumechange", () => {
  status.textContent = video.muted || video.volume === 0 ? "The player is muted. Click Play with sound to unmute." : "Sound is on.";
});
video.addEventListener("pause", () => { if (!video.ended) status.textContent = "Paused."; });
video.addEventListener("ended", () => { status.textContent = "Watch again, or read the full study below."; });
video.addEventListener("error", () => { status.textContent = "This browser could not play the video. Download it or use the original narration below."; });
original.addEventListener("play", () => video.pause());
