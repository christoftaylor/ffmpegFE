#!/bin/sh
#
# Converts video files into mp4 w/ h265 video and AC3 audio
# Keeps only English audio/subtitles, preserves select metadata

# Initialize variables
ARGS=""
CRF_VALUE=24
PROCEED_FLAG=0
DELETE_FLAG=0
SCALE_FLAG=0
STEREO_FLAG=0
INPUT=""
OUTPUT=""
VERBOSE_FLAG=0

# Parse in the arguments
while (( "$#" )); do
  case "$1" in
    -y|--no-prompt) PROCEED_FLAG=1; shift ;;
    -r|--rescale-to-720) SCALE_FLAG=1; shift ;;
    -a|--audio-to-stereo) STEREO_FLAG=1; shift ;;
    -v|--verbose) VERBOSE_FLAG=1; shift ;;
    -c|--crf-value)
      if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
        CRF_VALUE=$2
        shift 2
      else
        echo "Error: Argument for $1 is missing" >&2
        exit 1
      fi
      ;;
    -d|--delete) DELETE_FLAG=1; shift ;;
    -h|--help|"")
      echo
      echo "$0 is a wrapper for ffmpeg that simplifies the command line to a few switches"
      echo
      echo "$0 [options] input.xxx"
      echo
      echo "-a --audio-to-stereo    : converts to stereo, same as source if omitted"
      echo "-c n --crf-value n      : sets crf value, default to 28 if omitted"
      echo "-d --delete             : delete the input file, default is to keep it"
      echo "-r --rescale-to-720     : rescale to 720p, same as source if omitted"
      echo "-y --no-prompt          : dont stop to verify cmd before executing"
      echo "-v --verbose            : print out extra info"
      echo "-h --help               : this help message"
      echo
      exit 1
      ;;
    -*|--*=)
      echo "Error: Unsupported flag $1" >&2
      exit 1
      ;;
    *) ARGS="$ARGS $1"; shift ;;
  esac
done

INPUT=${ARGS:1}
[ -r "${INPUT}" ] || { echo "Cannot read file: ${INPUT}" >&1 ; exit 1 ; }

# Set output file name
if [[ "$INPUT" == *mp4 ]] || [[ -f "${INPUT%.???}.mp4" ]]; then
  OUTPUT=${INPUT%.???}.1.mp4
else
  OUTPUT=${INPUT%.???}.mp4
fi

echo "Input  = $INPUT"
echo "Output = $OUTPUT"

# Gather stream info using ffprobe (all fields in JSON)
STREAMS=$(ffprobe -v error -show_streams -of json "$INPUT")

# Initialize variables for mapping streams and metadata
MAP_CMD=" -map 0:v:0"  # Always include the first video stream
META_CMD=""
AUDIO_INDEX=0
SUB_INDEX=0

# Process audio streams
AUDIO_STREAMS=$(echo "$STREAMS" | jq -c '.streams[] | select(.codec_type=="audio" and (.tags.language=="eng"))')
if [[ -n "$AUDIO_STREAMS" ]]; then
  while IFS= read -r stream; do
    IDX=$(echo "$stream" | jq '.index')
    MAP_CMD="$MAP_CMD -map 0:$IDX"

    # Handle metadata disposition (default, forced, hearing_impaired)
    for tag in language default forced hearing_impaired; do
      VALUE=$(echo "$stream" | jq -r ".disposition.$tag // empty")
      if [[ -n "$VALUE" && "$VALUE" != "0" ]]; then
        META_CMD="$META_CMD -disposition:a:$AUDIO_INDEX $tag"
      fi
      if [[ "$tag" == "language" ]]; then
        LANG=$(echo "$stream" | jq -r ".tags.language // empty")
        if [[ -n "$LANG" ]]; then
          META_CMD="$META_CMD -metadata:s:a:$AUDIO_INDEX language=$LANG"
        fi
      fi
    done
    AUDIO_INDEX=$((AUDIO_INDEX+1))
  done <<< "$AUDIO_STREAMS" 
fi

# Process subtitle streams
SUB_STREAMS=$(echo "$STREAMS" | jq -c '.streams[] | select(.codec_type=="subtitle" and (.tags.language=="eng"))')
if [[ -n "$SUB_STREAMS" ]]; then
  while IFS= read -r stream; do
    IDX=$(echo "$stream" | jq '.index')
    MAP_CMD="$MAP_CMD -map 0:$IDX"
    for tag in language default forced hearing_impaired; do
      VALUE=$(echo "$stream" | jq -r ".disposition.$tag // empty")
      if [[ -n "$VALUE" && "$VALUE" != "0" ]]; then
        META_CMD="$META_CMD -disposition:s:$SUB_INDEX $tag"
      fi
      if [[ "$tag" == "language" ]]; then
        LANG=$(echo "$stream" | jq -r ".tags.language // empty")
        if [[ -n "$LANG" ]]; then
          META_CMD="$META_CMD -metadata:s:s:$SUB_INDEX language=$LANG"
        fi
      fi
    done
    SUB_INDEX=$((SUB_INDEX+1))
  done <<< "$SUB_STREAMS"
fi


# Verbose debug output
if [[ $VERBOSE_FLAG == 1 ]]; then
  echo
  echo "CRF      = $CRF_VALUE"
  echo "Stereo   = $STEREO_FLAG"
  echo "Rescale  = $SCALE_FLAG"
  echo "Delete   = $DELETE_FLAG"
  echo "Proceed  = $PROCEED_FLAG"
  echo
fi

# Build the ffmpeg command
FFCMD="ffmpeg -i \"$INPUT\" $MAP_CMD -map_metadata -1"
if [[ $SCALE_FLAG == 1 ]]; then
  FFCMD="$FFCMD -vf scale=-2:720"
fi
FFCMD="$FFCMD -c:v libx265 -preset slow -crf $CRF_VALUE"
FFCMD="$FFCMD -c:a eac3 -ab 128ki" 
FFCMD="$FFCMD -c:s mov_text"
if [[ $STEREO_FLAG == 1 ]]; then
  FFCMD="$FFCMD -ac 2"
fi
FFCMD="$FFCMD $META_CMD \"$OUTPUT\""

# Show command
echo
echo "The command will be:"
echo $FFCMD
echo

# Confirm execution if not skipped
if [[ $PROCEED_FLAG == 0 ]]; then
  read -p "Proceed? [Y] to cont., any other key to terminate. " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Execute the command
eval $FFCMD

# Handle cleanup
if [[ $DELETE_FLAG == 1 ]]; then
  if [ $? -eq 0 ]; then
    if [[ "$OUTPUT" == *.1.mp4 ]]; then 
      echo "Overwriting $INPUT"
      mv "$OUTPUT" "$INPUT"
    else
      echo "Deleting $INPUT"
      rm "$INPUT"
    fi
  else
    echo "Did not delete the input file because ffmpeg produced errors."
  fi
fi

