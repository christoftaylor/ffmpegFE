# Movieconverter.py
A text-based front end for ffmpeg that automates converting movie files using common settings.

Keeps the English audio and subtitle streams, and drops the others.
Strips out all the metadata, but then writes in titles for the audio and subtitle streams.
The container format and codecs are selectable, within a few common choices.

```
usage: movieconvert.py [-h] [-f {mp4,mkv}] [-v {copy,avc,hevc}] [-r] [-c CRF_VALUE] [-a {copy,aac,ac3,eac3}] [-2] [-s] [-d] [-y] [--verbose] input

A wrapper for ffmpeg to simplify video conversion.

positional arguments:
  input                 Input video file

options:
  -h, --help            show this help message and exit
  -f, --container {mp4,mkv}
                        Set output container format (choose: mp4 or mkv; default: mp4)
  -v, --video-codec {copy,avc,hevc}
                        Set output video codec (choose: avc (h264) or hevc (h265); default: hevc)
  -r, --rescale-to-720  Rescale video to 720p
  -c, --crf-value CRF_VALUE
                        Set CRF value (lower for higher quality; higher for higher compression; 17-28 is sane) (default: 28 for hevc, 23 for avc)
  -a, --audio-codec {copy,aac,ac3,eac3}
                        Set output audio codec (choose: copy, aac, ac3, eac3; default: eac3)
  -2, --audio-to-stereo
                        Convert audio to stereo
  -s, --subtitle        Ignore subtitles, included by default
  -d, --delete          Delete the input file after conversion
  -y, --no-prompt       Don't ask for confirmation before executing
  --verbose             Print extra information
```





