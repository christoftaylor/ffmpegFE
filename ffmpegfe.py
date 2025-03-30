#!/usr/bin/env python3
#
# A script that provides an interactive wizard to build an ffmpeg command

import subprocess
import json
import urwid
import sys
import os
import re

def get_output_filename(file_path):
    base, ext = os.path.splitext(file_path)
    return f"{base}.1.mp4" if ext.lower() == ".mp4" else f"{base}.mp4"

def get_srt_filenames(file_path):
    base, _ = os.path.splitext(os.path.basename(file_path))
    subtitle_files = []
    directory = os.path.dirname(file_path)
    
    for filename in os.listdir(directory):
        if filename.lower().endswith(".srt") and base in filename:
            match = re.match(r"^(.+?)(?:\.([a-z]{2}))?(?:\.(forced))?(?:\.(sdh))?\.srt$", filename.lower())
            if match:
                lang = match.group(2) if match.group(2) else "en"
                forced = 1 if match.group(3) else 0
                sdh = 1 if match.group(4) else 0
                subtitle_files.append((os.path.join(directory, filename), lang, forced, sdh))

    return subtitle_files if subtitle_files else [("No srt files present", "en", 0, 0)]

def get_streams(file_path):
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-of", "json", file_path]
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        streams = json.loads(result.stdout)["streams"]
    except (json.JSONDecodeError, KeyError):
        return [], "Error: Could not retrieve stream information."

    video_streams, audio_streams, subtitle_streams = [], [], []
    
    for s in streams:
        codec_type = s.get('codec_type', 'Unknown').capitalize()
        codec_name = s.get('codec_name', 'Unknown')
        resolution = f"{s.get('width', 'N/A')}x{s.get('height', 'N/A')}" if codec_type == 'Video' else None
        language = s.get('tags', {}).get('language', 'N/A')
        title = s.get('tags', {}).get('title', 'N/A')
        forced = s.get('tags', {}).get('forced', 'N/A')

        if codec_type == 'Video':
            video_streams.append({'index': s.get('index', 'N/A'), 'codec_name': codec_name, 'resolution': resolution})
        elif codec_type == 'Audio':
            audio_streams.append({'index': s.get('index', 'N/A'), 'codec_name': codec_name, 'language': language, 'title': title})
        elif codec_type == 'Subtitle':
            subtitle_streams.append({'index': s.get('index', 'N/A'), 'language': language, 'forced': forced, 'title': title})

    return video_streams, audio_streams, subtitle_streams

def exit_program(button, loop=None):
    raise urwid.ExitMainLoop()

def close_dialog(button, frame, loop):
    frame.body = main_menu_pile  # Restore main menu
    loop.draw_screen()  # Refresh UI

def show_dialog(dialog_content, frame, loop):
    body = urwid.Text(dialog_content)
    close_button = urwid.Button("Close")
    urwid.connect_signal(close_button, "click", lambda button: close_dialog(button, frame, loop))

    pile = urwid.Pile([body, urwid.Divider(), close_button])
    dialog = urwid.LineBox(urwid.Padding(pile, left=2, right=2))

    frame.body = urwid.Overlay(
        dialog, frame.body,
        align='center', width=('relative', 50),
        valign='middle', height=('relative', 30),
        min_width=20, min_height=9
    )

    loop.draw_screen()  # Update UI immediately

def show_stream_dialog(button, frame, loop):
    show_dialog("Select streams.\nPress Close to return.", frame, loop)

def show_codec_dialog(button, frame, loop):
    show_dialog("Select codec options.\nPress Close to return.", frame, loop)

def show_subtitle_dialog(button, frame, loop):
    show_dialog("Select subtitle options.\nPress Close to return.", frame, loop)

class FocusableListBox(urwid.ListBox):
    def keypress(self, size, key):
        if key == 'left':
            return None  # Prevent left arrow from moving focus
        elif key == 'q':
            raise urwid.ExitMainLoop()  # Quit program when 'q' is pressed
        return super().keypress(size, key)

def main():
    global frame, main_menu_pile

    if len(sys.argv) != 2:
        print("Usage: python script.py <video_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    output_file = get_output_filename(file_path)
    srt_files = get_srt_filenames(file_path)
    video_streams, audio_streams, subtitle_streams = get_streams(file_path)

    video_codec = 'hevc'
    audio_codec = 'ac3'
    subtitle_mode = 'Separate streams'

    video_resolution = video_streams[0]['resolution'] if video_streams else '1280x768'
    audio_language = audio_streams[0]['language'] if audio_streams else 'eng'
    subtitle_language = subtitle_streams[0]['language'] if subtitle_streams else 'en'

    input_text = urwid.Text(f"Input  : {file_path}")
    blank_line = urwid.Text("")

    subtitle_widgets = [urwid.Text(f"Srt #{index} : {srt[0]}") for index, srt in enumerate(srt_files)] if srt_files != "No srt files present" else [urwid.Text("Subtitle : No srt files present")]

    stream_widgets = [urwid.Text(f"Stream #{index} : {stream['codec_name']}, {video_resolution if 'resolution' in stream else audio_language}") for index, stream in enumerate(video_streams + audio_streams)]

    output_text = urwid.Text(f"Output : {output_file}")

    codec_widgets = [
        urwid.Text(f"Stream #0 : video, {video_codec}, {video_resolution}"),
        urwid.Text(f"Stream #1 : audio, {audio_codec}, {audio_language}")
    ]

    left_top_pane = urwid.LineBox(FocusableListBox(urwid.SimpleFocusListWalker([blank_line, input_text, blank_line] + stream_widgets + [blank_line] + subtitle_widgets)), title="Input")
    left_bottom_pane = urwid.LineBox(FocusableListBox(urwid.SimpleFocusListWalker([blank_line, output_text, blank_line] + codec_widgets)), title="Output")
    left_pane = urwid.Pile([("weight", 1, left_top_pane), ("weight", 1, left_bottom_pane)])

    frame = urwid.Frame(body=left_pane)
    loop = urwid.MainLoop(frame)  # Create the MainLoop once

    menu_options = [
        urwid.Button("Select Streams", lambda button: show_stream_dialog(button, frame, loop)),
        urwid.Button("Select Codecs", lambda button: show_codec_dialog(button, frame, loop)),
        urwid.Button("Select Subtitles", lambda button: show_subtitle_dialog(button, frame, loop)),
        urwid.Button("Quit", exit_program)
    ]

    right_pane = urwid.LineBox(FocusableListBox(urwid.SimpleFocusListWalker(menu_options)), title="Options")

    columns = urwid.Columns([("weight", 2, left_pane), ("weight", 1, right_pane)], 0, 1)
    main_menu_pile = urwid.Pile([columns])

    frame.body = main_menu_pile
    loop.run()  # Run the UI loop only once

if __name__ == "__main__":
    main()

