#!/usr/bin/env python3
#
# A script that automates building an ffmpeg command


import argparse
import json
import os
import subprocess
import sys

def crf_range(value):
    ivalue = int(value)
    if ivalue < 0 or ivalue > 51:
        raise argparse.ArgumentTypeError(f"CRF value must be between 0 and 51, but got {value}.")
    return ivalue

def main():
    parser = argparse.ArgumentParser(
        description="A wrapper for ffmpeg to simplify video conversion."
    )
    parser.add_argument("input", 
                        help="Input video file")
    parser.add_argument("-f", "--container", type=str, choices=["mp4", "mkv"], default="mp4", 
                        help="Set output container format (choose: mp4 or mkv; default: mp4)")
    parser.add_argument("-v", "--video-codec", type=str, choices=["copy", "avc", "hevc"], default="hevc", 
                        help="Set output video codec (choose: avc (h264) or hevc (h265); default: hevc)")
    parser.add_argument("-r", "--rescale-to-720", action="store_true", 
                        help="Rescale video to 720p")
    parser.add_argument("-c", "--crf-value", type=crf_range,  
                        help="Set CRF value (lower for higher quality; higher for higher compression; 17-28 is sane) (default: 28 for hevc, 23 for avc)")
    parser.add_argument("-a", "--audio-codec", type=str, choices=["copy", "aac", "ac3", "eac3"], default="eac3", 
                        help="Set output audio codec (choose: copy, aac, ac3, eac3; default: eac3)")
    parser.add_argument("-2", "--audio-to-stereo", action="store_true", 
                        help="Convert audio to stereo")
    parser.add_argument("-s", "--subtitle", action="store_false", 
                        help="Ignore subtitles, included by default")
    parser.add_argument("-d", "--delete", action="store_true", 
                        help="Delete the input file after conversion")
    parser.add_argument("-y", "--no-prompt", action="store_true", 
                        help="Don't ask for confirmation before executing")
    parser.add_argument("--verbose", action="store_true",
                        help="Print extra information")
    args = parser.parse_args()

    # Validate CRF value input and set default if not provided
    if args.crf_value is None:
        if args.video_codec == "avc":
            args.crf_value = 20
        elif args.video_codec == "hevc":
            args.crf_value = 24
    elif args.crf_value < 0 or args.crf_value > 51:
        print("Error: CRF value must be between 0 and 51.")
        sys.exit(1)

    # Validate input file
    input_file = args.input
    if not os.path.isfile(input_file):
        print(f"Error: Cannot read file '{input_file}'")
        sys.exit(1)

    # Determine output file name
    base, ext = os.path.splitext(input_file)
    # Set the extension based on the selected container format
    output_file = f"{base}.{args.container}"
    # Add a number if the output file already exists
    counter = 1
    while os.path.isfile(output_file):
        output_file = f"{base}.{counter}.{args.container}"
        counter += 1

    # Determine if subtitle file is present
    subfile = None
    if os.path.isfile(f"{base}.srt"):
        subfile = f"{base}.srt"
    else:
        # Check for language-specific .srt files (e.g., .en.srt)
        for lang_code in ["en", "eng"]:
            lang_subfile = f"{base}.{lang_code}.srt"
            if os.path.isfile(lang_subfile):
                subfile = lang_subfile
                break

    # Determine if any subtitle files are present
    subfiles_in = []
    directory = os.path.dirname(input_file) or "."
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    i = 1
    for filename in os.listdir(directory):
        if filename.lower().endswith(".srt") and base_name in filename:
            # Extract metadata from the filename
            parts = filename[len(base_name):].lower().split(".")
            lang = "eng" # assume English if no language specified
            forced = 0
            sdh = 0
            # Parse the parts of the filename
            title_parts = []
            for part in parts:
                if part in ["en", "eng"]:  # Language codes
                    lang = "eng"
                    title_parts.append("English")
                elif part == "forced":  # Forced tag
                    forced = 1
                    title_parts.append("Forced")
                elif part == "sdh":  # SDH tag
                    sdh = 1
                    title_parts.append("SDH")
            if title_parts:
                title = " ".join(title_parts)
            else:
                title = "English"
            # Add the subtitle file to subfiles_in
            subfiles_in.append({
                "index": i,
                "codec": "srt",
                "language": lang,
                "default": 0,  
                "forced": forced,
                "sdh": sdh,
                "title": title,
                "filename": os.path.join(directory, filename)
            })
            i += 1


    # get stream information using ffprobe
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", input_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        streams = json.loads(result.stdout)["streams"]
    except (json.JSONDecodeError, KeyError):
        return [], "Error: Could not retrieve stream information."

    # parse all the streams into buckets by stream type
    # keep select streams for the output file
    video_streams_in, audio_streams_in, subtitle_streams_in = [], [], []
    video_streams_out, audio_streams_out, subtitle_streams_out = [], [], []
    for s in streams:
        codec_type = s.get('codec_type', 'Unknown').capitalize()
        codec_name = s.get('codec_name', 'Unknown')
        resolution = f"{s.get('width', 'N/A')}x{s.get('height', 'N/A')}" if codec_type == 'Video' else None
        newtitle_parts = []
        language = s.get('tags', {}).get('language', 'eng')
        language = 'eng' if language == 'und' else language  # If language is undefined, set it to 'eng'
        newtitle_parts.append("English" if language == 'eng' else language) 
        title = s.get('tags', {}).get('title', '')
        default = s.get('disposition', {}).get('default', '0')
        forced = s.get('disposition', {}).get('forced', '0')
        newtitle_parts.append("Forced") if forced == '1' or 'forced' in title.lower() else None
        sdh = s.get('disposition', {}).get('hearing_impaired', '0')
        newtitle_parts.append("SDH") if sdh == '1' or 'sdh' in title.lower() else None
        newtitle = " ".join(newtitle_parts)
        # build sream info for input and output
        if codec_type == 'Video':
            video_streams_in.append({
                'index': s.get('index', 'N/A'),
                'codec': codec_name,
                'resolution': resolution,
                'title': title})
            video_streams_out.append({
                'index': s.get('index', 'N/A'),
                'codec': args.video_codec if args.video_codec != "copy" else codec_name,
                'resolution': "-2x720" if args.rescale_to_720 else resolution,
                'title': "N/A"})
        elif codec_type == 'Audio':
            audio_streams_in.append({
                'index': s.get('index', 'N/A'),
                'codec': codec_name,
                'language': s.get('tags', {}).get('language', 'N/A'),
                'channels': s.get('channels', 'N/A'),
                'title': title})
            if len(audio_streams_in) == 1 or language == 'eng':
                audio_streams_out.append({
                    'index': s.get('index', 'N/A'),
                    'codec': args.audio_codec if args.audio_codec != "copy" else codec_name,
                    'language': language if language != 'N/A' else 'eng',
                    'channels': s.get('channels', 'N/A'),
                    'title': newtitle})
        elif codec_type == 'Subtitle':
            disposition = s.get('disposition', {})
            subtitle_streams_in.append({
                'index': s.get('index', 'N/A'),
                'codec': codec_name,
                'language': language,
                'default': default,
                'forced': forced,
                'sdh': sdh,
                'title': title})
            if language == 'eng' or language == 'N/A':
                subtitle_streams_out.append({
                    'index': s.get('index', 'N/A'),
                    'codec': codec_name,
                    'language': language,
                    'default': default,
                    'forced': 1 if 'forced' in title.lower() else forced,
                    'sdh': 1 if 'sdh' in title.lower() else sdh,
                    'title': newtitle})

    # print stream information for input file
    print()
    print("Input file:  ", input_file)
    print("  Video:")
    for stream in video_streams_in:
        print("    " + ", ".join(f"{key}: {value}" for key, value in stream.items()))
    print("  Audio:")
    for stream in audio_streams_in:
        print("    " + ", ".join(f"{key}: {value}" for key, value in stream.items()))
    print("  Subtitles:")
    for stream in subtitle_streams_in:
        print("    " + ", ".join(f"{key}: {value}" for key, value in stream.items()))

    # print stream information for subtitle file if present
    if args.subtitle and subfiles_in:
        print()
        print("Subtitle file:")    
        print("  Subtitles:")
        for file in subfiles_in:
            print("    " + ", ".join(f"{key}: {value}" for key, value in file.items() if key != "title"))
    print()

    # print stream information for output file
    print()
    print("Output file: ", output_file)
    print("  Video:")
    for stream in video_streams_out:
        print("    " + ", ".join(f"{key}: {value}" for key, value in stream.items()))
    print("  Audio:")
    for stream in audio_streams_out:
        print("    " + ", ".join(f"{key}: {value}" for key, value in stream.items()))
    if args.subtitle:
        print("  Subtitles:")
        for stream in subtitle_streams_out:
            print("    " + ", ".join(f"{key}: {value}" for key, value in stream.items()))
        s = len(subtitle_streams_out) + len(audio_streams_out) + len(video_streams_out)
        for i, stream in enumerate(subfiles_in):
            k = i + s
            print(f"    index: {k}, " + ", ".join(f"{key}: {value}" for key, value in list(stream.items())[1:-1]))
    print()

    ###########################################################################
    # Build ffmpeg command
    cmd = ["ffmpeg", "-i", input_file]

    # Include subtitle file if present
    if args.subtitle:
        for file in subfiles_in:
            cmd.extend(["-f", "srt", "-i", file['filename']])

    # Remove metadata and chapters
    cmd.extend(["-map_metadata", "-1", "-map_chapters", "-1"])

    # Map video streams
    for stream in video_streams_out:
        cmd.extend(["-map", f"0:{stream['index']}"])

    # Map audio streams
    for stream in audio_streams_out:
        cmd.extend(["-map", f"0:{stream['index']}"])

    # Map subtitle streams
    if args.subtitle:
        for stream in subtitle_streams_out:
            cmd.extend(["-map", f"0:{stream['index']}"])

    # Map subtitle file(s) if present
    if args.subtitle:
        for file in subfiles_in:
            cmd.extend(["-map", f"{file['index']}:0"])    
    
    # Video settings
    if args.video_codec == "copy":
        cmd.extend(["-c:v", "copy"])
    elif args.video_codec == "avc":
        cmd.extend(["-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", str(args.crf_value)])
    elif args.video_codec == "hevc":
        cmd.extend(["-c:v", "libx265", "-preset", "slow", "-crf", str(args.crf_value), "-tag:v", "hvc1"])

    # Scaling
    if args.rescale_to_720:
        cmd.extend(["-vf", "scale=-2:720"])

    # Audio settings
    if args.audio_codec == "copy":
        cmd.extend(["-c:a", "copy"])
    elif args.audio_codec == "aac":
        cmd.extend(["-c:a", "aac"])
    elif args.audio_codec == "ac3":
        cmd.extend(["-c:a", "ac3"])
    elif args.audio_codec == "eac3":    
        cmd.extend(["-c:a", "eac3"])
    if args.audio_to_stereo:
        cmd.extend(["-ac", "2"])

    # Subtitle settings
    if args.subtitle:
        # Set subtitle codec
        cmd.extend(["-c:s", "mov_text"])  

    # Set audio language metadata
    for stream in audio_streams_out:
        if stream.get('language'):  
            cmd.extend([f"-metadata:s:a:{stream['index']-1}", f"language={stream['language']}"])
        if stream.get('title'):  
            cmd.extend([f"-metadata:s:a:{stream['index']-1}", f"title={stream['title']}"])

    # Set subtitle metadata
    if args.subtitle:
        for i, stream in enumerate(subtitle_streams_out):
            # Set metadata for each subtitle stream
            disposition_parts = []
            if stream.get('forced', 1):
                disposition_parts.append("+forced")
            if stream.get('sdh', 1):
                disposition_parts.append("+hearing_impaired")
            disposition_str = "".join(disposition_parts) if disposition_parts else None
            if stream.get('language'):  
                cmd.extend([f"-metadata:s:s:{i}", f"language={stream['language']}"])
            if stream.get('title') and stream.get('title') != "N/A":  
                cmd.extend([f"-metadata:s:s:{i}", f"title={stream['title']}"])
            if disposition_str:  
                cmd.extend([f"-disposition:s:{i}", disposition_str])
        # continue setting subtitle metadata for subtitle files, if any
        if subfiles_in:
            starting_index = len(subtitle_streams_out)  # Start after the last subtitle stream in above
            for j, file in enumerate(subfiles_in):
                i = starting_index + j
                disposition_parts = []
                if file.get('forced', 1):
                    disposition_parts.append("+forced")
                if file.get('sdh', 1):
                    disposition_parts.append("+hearing_impaired")
                disposition_str = "".join(disposition_parts) if disposition_parts else None
                if file.get('language'):  
                    cmd.extend([f"-metadata:s:s:{i}", f"language={file['language']}"])
                if file.get('title') and file.get('title') != "N/A":  
                    cmd.extend([f"-metadata:s:s:{i}", f"title={file['title']}"])
                if disposition_str:  
                    cmd.extend([f"-disposition:s:{i}", disposition_str])

    # Output file
    cmd.append(output_file)

    # Print the command
    print("\nThe command will be:")
    print(" ".join(cmd))
    print()
    if args.delete:
        print("The input file(s) will be deleted after conversion.")
    print()

    # Confirm execution
    if not args.no_prompt:
        proceed = input("Proceed? [Y] to continue, any other key to terminate: ").strip().lower()
        if proceed != "y":
            print("Aborted.")
            sys.exit(0)

    ###########################################################################
    # Execute the command
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: ffmpeg command failed with error: {e}")
        sys.exit(1)


    # Delete the input file if specified
    if args.delete:
        # Handle renaming or deleting the input file
        if input_file and os.path.isfile(input_file):
            print(f"Deleting:  {input_file}")
            os.remove(input_file)
        # Handle renaming or deleting the output file if it has a numbered suffix
        base, ext = os.path.splitext(input_file)
        output_base, output_ext = os.path.splitext(output_file)
        if output_base.endswith(f".{counter - 1}") and output_ext == f".{args.container}":
            new_input_file = f"{base}.{args.container}"  # Ensure the correct extension
            print(f"Renaming:  {output_file} -> {new_input_file}")
            os.rename(output_file, new_input_file)
        # Delete subtitle files included as inputs
        for subfile in subfiles_in:
            subtitle_file = subfile.get("filename")
            if subtitle_file and os.path.isfile(subtitle_file):
                print(f"Deleting:  {subtitle_file}")
                os.remove(subtitle_file)

if __name__ == "__main__":
    main()
