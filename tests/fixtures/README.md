# Parser fixtures

`probe.json` is a minimal, handcrafted ffprobe-shaped document for a fictional
four-second portrait video. It deliberately uses a rational average frame rate.

The `.log` files are captured filter-only excerpts from the FFmpeg 7.1 Windows
binary bundled with imageio-ffmpeg. Memory addresses were replaced with
`ADDRESS`; no media paths or personal data are included. These commands generate
their sources entirely in memory:

```console
ffmpeg -hide_banner -nostdin -nostats -f lavfi -i color=c=black:size=96x160:rate=30 -t 3 -vf freezedetect=n=-60dB:d=0.001,blackdetect=d=0.001 -f null -
ffmpeg -hide_banner -nostdin -nostats -f lavfi -i sine=frequency=440 -t 3 -af silencedetect=n=-50dB:d=0.001,astats=reset=0,loudnorm=I=-14:print_format=json -f null -
ffmpeg -hide_banner -nostdin -nostats -f lavfi -i anullsrc=r=44100:cl=mono -t 3 -af silencedetect=n=-50dB:d=0.001,astats=reset=0,loudnorm=I=-14:print_format=json -f null -
```

The files are `video.log`, `audio.log`, and `silence.log`, respectively. Filter
diagnostic lines and loudnorm JSON were retained in their original order. The
open freeze event exercises EOF closure; silence includes `-inf` measurements.
Additional unit tests cover CRLF, scientific notation, completed events, channel
peak selection, malformed output, and unrelated log noise.

`ffmpeg_h264_aac.log`, `ffmpeg_video_only.log`, and `ffmpeg_audio_only.log` are
captured `ffmpeg -hide_banner -i` stderr samples used to verify the fallback
stream metadata parser when ffprobe is absent.

`silence_trailing.log` is a captured real output exercising AAC trailing silence
intervals (`silence_start: 3.001`, `silence_end: 3.018` for a 3.0s stream) that
must be ignored to prevent false failures when `max_silence` is 0.
