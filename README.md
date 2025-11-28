# Movieconverter.py
A text-based front end for ffmpeg that automates converting movie files using common settings.  
  
By default, it converts whatever into h265 video and eac3 audio inside a MP4 container.  
The container format and codecs are selectable, within a few common choices.  
Keeps the English audio and subtitle streams, and drops any other languages.  
Strips out all the metadata, but then writes in titles for the audio and subtitle streams.  
It presents the ffmpeg command, but what is presented lacks quotes around file names and strings, so it can't be directly copy pasted.  
  
  
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
  
Example:
```
> ./movieconvert.py test.mkv 

Input file:   test.mkv
  Video:
    index: 0, codec: h264, resolution: 1280x720, title: Test.h264.aac.movie
  Audio:
    index: 1, codec: aac, language: eng, channels: 2, title: English
  Subtitles:

Subtitle file:
  Subtitles:
    index: 1, codec: srt, language: eng, default: 0, forced: 0, sdh: 0, filename: ./test.en.srt


Output file:  test.1.mp4
  Video:
    index: 0, codec: hevc, resolution: 1280x720, title: N/A
  Audio:
    index: 1, codec: eac3, language: eng, channels: 2, title: English
  Subtitles:
    index: 2, codec: srt, language: eng, default: 0, forced: 0, sdh: 0, title: English


The command will be:
ffmpeg -i test.mkv -f srt -i ./test.en.srt -map_metadata -1 -map_chapters -1 -map 0:0 -map 0:1 -map 1:0 -c:v libx265 -preset slow -crf 24 -tag:v hvc1 -c:a eac3 -c:s mov_text -metadata:s:a:0 language=eng -metadata:s:a:0 title=English -metadata:s:s:0 language=eng -metadata:s:s:0 title=English test.1.mp4


Proceed? [Y] to continue, any other key to terminate: 
```



