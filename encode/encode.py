from pathlib import Path
import subprocess
import sys
import os
import json



def encode_video_with_burn(input_file, output_file, font_path, text, x, y, fontsize, fontcolor,
                          bitrate, audio_bitrate, maxrate, bufsize, pix_fmt, sample_rate,
                          resolution, burn_subtitle=None, logo_path=None, logo_x=10, logo_y=10, 
                          logo_scale=None, audio_file=None, audio_lang='eng'):
    """
    Encode video with burned-in subtitle and logo (single audio track).
    
    Args:
        burn_subtitle: Path to subtitle file to burn into video
        logo_path: Path to logo image file (PNG/JPG)
        logo_x, logo_y: Logo position
        logo_scale: Logo scale (e.g., '100:100' or 'iw*0.1:-1' for 10% width)
        audio_file: Single audio file to replace original audio
        audio_lang: Language code for audio track
    """
    print(f"Processing (Burn Mode): {input_file} -> {output_file}")

    # Build video filter chain
    filters = [f"scale={resolution}"]
    
    # Add burned subtitle
    if burn_subtitle:
        filters.append(f"subtitles='{burn_subtitle}'")
    
    # Add logo overlay
    if logo_path:
        if logo_scale:
            logo_filter = f"overlay={logo_x}:{logo_y}:enable='between(t,0,inf)'"
            # We need to use complex filter for logo
            filters = [f"[0:v]scale={resolution}[scaled]"] + \
                     ([f"[scaled]subtitles='{burn_subtitle}'[subbed]"] if burn_subtitle else []) + \
                     [f"[{'subbed' if burn_subtitle else 'scaled'}]overlay={logo_x}:{logo_y}:enable='between(t,0,inf)'[final]"]
        else:
            filters.append(f"overlay={logo_x}:{logo_y}:enable='between(t,0,inf)'")
    
    # Add text overlay
    filters.append(
        f"drawtext=fontfile='{font_path}':text='{text}':x={x}:y={y}:fontsize={fontsize}:fontcolor={fontcolor}"
    )

    # Start building ffmpeg command
    ffmpeg_cmd = ["ffmpeg", "-threads", "0", "-i", input_file]
    
    # Add logo as input if provided
    if logo_path:
        ffmpeg_cmd += ["-i", logo_path]
    
    # Add audio file if provided
    if audio_file:
        ffmpeg_cmd += ["-i", audio_file]

    # Apply filters
    if logo_path and logo_scale:
        # Complex filter for logo with scaling
        filter_chain = ";".join(filters)
        ffmpeg_cmd += ["-filter_complex", filter_chain, "-map", "[final]"]
    else:
        filter_complex = ",".join(filters)
        ffmpeg_cmd += ["-vf", filter_complex, "-map", "0:v"]

    # Map audio
    if audio_file:
        audio_input_index = 2 if logo_path else 1
        ffmpeg_cmd += ["-map", f"{audio_input_index}:a"]
    else:
        ffmpeg_cmd += ["-map", "0:a"]

    # Video encoding settings
    ffmpeg_cmd += [
        "-c:v", "libx264",
        "-profile:v", "high",
        "-pix_fmt", pix_fmt,
        "-b:v", bitrate,
        "-maxrate", maxrate,
        "-bufsize", bufsize,
        "-preset", "medium",
    ]

    # Audio encoding settings
    if audio_file:
        ffmpeg_cmd += [
            "-c:a", "copy",
            f"-metadata:s:a:0", f"language={audio_lang}"
        ]
    else:
        ffmpeg_cmd += [
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-ar", str(sample_rate),
            "-ac", "2",
        ]

    # Global flags and output
    ffmpeg_cmd += [
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-movflags", "+faststart",
        "-dn",
        output_file
    ]

    print("Running FFmpeg (Burn Mode):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Encoding failed!", file=sys.stderr)
        sys.exit(1)


def encode_video_with_soft_tracks(input_file, output_file, font_path, text, x, y, fontsize, fontcolor,
                                 bitrate, audio_bitrate, maxrate, bufsize, pix_fmt, sample_rate,
                                 resolution, audio_tracks=None, subtitles=None):
    """
    Encode video with multiple soft audio tracks and subtitles (no burning).
    
    Args:
        audio_tracks: List of dicts with 'file', 'language', 'default', 'forced' keys
                     Example: [{'file': 'ar.m4a', 'language': 'ara', 'default': True, 'forced': True},
                              {'file': 'en.m4a', 'language': 'eng', 'default': False, 'forced': False}]
        subtitles: List of dicts with 'file', 'language', 'default', 'forced' keys
                  Example: [{'file': 'ar.vtt', 'language': 'ara', 'default': True, 'forced': True},
                           {'file': 'en.vtt', 'language': 'eng', 'default': False, 'forced': False}]
    """
    print(f"Processing (Soft Tracks): {input_file} -> {output_file}")

    # Build video filter chain: scaling + text overlay (no burning)
    filters = [f"scale={resolution}"]
    filters.append(
        f"drawtext=fontfile='{font_path}':text='{text}':x={x}:y={y}:fontsize={fontsize}:fontcolor={fontcolor}"
    )
    filter_complex = ",".join(filters)

    # Start building ffmpeg command
    ffmpeg_cmd = ["ffmpeg", "-threads", "0", "-i", input_file]
    
    input_index = 1  # Track input file index (0 is main video)
    
    # Add audio track inputs
    audio_map_info = []
    if audio_tracks:
        for i, audio in enumerate(audio_tracks):
            ffmpeg_cmd += ["-i", audio['file']]
            audio_map_info.append({
                'index': input_index,
                'stream_index': i,
                'language': audio.get('language', 'und'),
                'default': audio.get('default', False),
                'forced': audio.get('forced', False)
            })
            input_index += 1
    
    # Add subtitle inputs
    subtitle_map_info = []
    if subtitles:
        for i, subtitle in enumerate(subtitles):
            ffmpeg_cmd += ["-i", subtitle['file']]
            subtitle_map_info.append({
                'index': input_index,
                'stream_index': i,
                'language': subtitle.get('language', 'und'),
                'default': subtitle.get('default', False),
                'forced': subtitle.get('forced', False)
            })
            input_index += 1

    # Apply video filters
    ffmpeg_cmd += ["-vf", filter_complex]

    # Map video stream
    ffmpeg_cmd += ["-map", "0:v"]
    
    # Map audio streams
    if audio_tracks:
        for audio_info in audio_map_info:
            ffmpeg_cmd += ["-map", f"{audio_info['index']}:a"]
    else:
        # Default: map original audio
        ffmpeg_cmd += ["-map", "0:a"]
    
    # Map subtitle streams
    if subtitles:
        for subtitle_info in subtitle_map_info:
            ffmpeg_cmd += ["-map", f"{subtitle_info['index']}"]

    # Video encoding settings
    ffmpeg_cmd += [
        "-c:v", "libx264",
        "-profile:v", "high",
        "-pix_fmt", pix_fmt,
        "-b:v", bitrate,
        "-maxrate", maxrate,
        "-bufsize", bufsize,
        "-preset", "medium",
    ]

    # Audio encoding settings
    if audio_tracks:
        ffmpeg_cmd += ["-c:a", "copy"]  # Copy audio streams as-is
        # Add metadata for each audio stream
        for i, audio_info in enumerate(audio_map_info):
            ffmpeg_cmd += [f"-metadata:s:a:{i}", f"language={audio_info['language']}"]
            
            # Set disposition flags
            disposition = []
            if audio_info['default']:
                disposition.append("default")
            if audio_info['forced']:
                disposition.append("forced")
            if disposition:
                ffmpeg_cmd += [f"-disposition:a:{i}", "+".join(disposition)]
    else:
        # Default audio encoding
        ffmpeg_cmd += [
            "-c:a", "aac",
            "-b:a", audio_bitrate,
            "-ar", str(sample_rate),
            "-ac", "2",
        ]

    # Subtitle stream encoding and metadata
    if subtitles:
        ffmpeg_cmd += ["-c:s", "mov_text"]
        for i, subtitle_info in enumerate(subtitle_map_info):
            ffmpeg_cmd += [f"-metadata:s:s:{i}", f"language={subtitle_info['language']}"]
            
            # Set disposition flags
            disposition = []
            if subtitle_info['default']:
                disposition.append("default")
            if subtitle_info['forced']:
                disposition.append("forced")
            if disposition:
                ffmpeg_cmd += [f"-disposition:s:{i}", "+".join(disposition)]

    # Global flags and output
    ffmpeg_cmd += [
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-movflags", "+faststart",
        "-dn",
        output_file
    ]

    print("Running FFmpeg (Soft Tracks):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Encoding failed!", file=sys.stderr)
        sys.exit(1)



def create_multi_resolution_videos(input_file, output_dir, base_filename=None, custom_resolutions=None):
    """
    Create multiple resolution versions of a video file.
    
    Args:
        input_file: Path to input video file
        output_dir: Directory to save output files
        base_filename: Base name for output files (without extension)
        custom_resolutions: List of custom resolution configs, if None uses default
    
    Returns:
        List of created file paths
    """
    
    # Default resolution configurations
    default_resolutions = [
        {
            'resolution': '1280x720',
            'height': 720,
            'bitrate': '2500k',
            'maxrate': '2675k',
            'bufsize': '3750k',
            'audio_bitrate': '128k'
        },
        {
            'resolution': '854x480', 
            'height': 480,
            'bitrate': '1000k',
            'maxrate': '1100k',
            'bufsize': '1500k',
            'audio_bitrate': '128k'
        },
        {
            'resolution': '640x360',
            'height': 360, 
            'bitrate': '600k',
            'maxrate': '660k',
            'bufsize': '900k',
            'audio_bitrate': '96k'
        }
    ]
    
    # Use custom resolutions if provided, otherwise use defaults
    resolutions = custom_resolutions if custom_resolutions else default_resolutions
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get base filename from input if not provided
    if base_filename is None:
        base_filename = Path(input_file).stem
    
    created_files = []
    
    for config in resolutions:
        # Generate output filename
        output_filename = f"{base_filename}_{config['height']}p.mp4"
        output_path = os.path.join(output_dir, output_filename)
        
        print(f"\n{'='*60}")
        print(f"Creating {config['height']}p version...")
        print(f"{'='*60}")
        
        # Build ffmpeg command for simple resolution conversion
        ffmpeg_cmd = [
            "ffmpeg", "-threads", "0", "-i", input_file,
            "-vf", f"scale={config['resolution']}",
            "-c:v", "libx264",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
            "-b:v", config['bitrate'],
            "-maxrate", config['maxrate'],
            "-bufsize", config['bufsize'],
            "-preset", "medium",
            "-c:a", "aac",
            "-b:a", config['audio_bitrate'],
            "-ar", "48000",
            "-ac", "2",
            "-movflags", "+faststart",
            "-dn",
            output_path
        ]
        
        print("Running FFmpeg:\n" + " ".join(ffmpeg_cmd))
        process = subprocess.run(ffmpeg_cmd)
        if process.returncode != 0:
            print(f"Error: Encoding failed for {config['height']}p!", file=sys.stderr)
            continue
        
        created_files.append({
            'resolution': config['height'],
            'file_path': output_path,
            'bitrate': config['bitrate'],
            'maxrate': config['maxrate']
        })
        
        print(f"✅ Created: {output_path}")
    
    return created_files


def add_subtitles_and_audio_only(input_file, output_file, audio_tracks=None, subtitles=None):
    """
    Add only subtitles and audio tracks to video without any other processing.
    
    Args:
        input_file: Path to input video file
        output_file: Path to output video file
        audio_tracks: List of dicts with 'file', 'language', 'default', 'forced' keys
        subtitles: List of dicts with 'file', 'language', 'default', 'forced' keys
    """
    print(f"Adding subtitles and audio: {input_file} -> {output_file}")

    # Start building ffmpeg command
    ffmpeg_cmd = ["ffmpeg", "-threads", "0", "-i", input_file]
    
    input_index = 1
    
    # Add audio track inputs
    audio_map_info = []
    if audio_tracks:
        for i, audio in enumerate(audio_tracks):
            ffmpeg_cmd += ["-i", audio['file']]
            audio_map_info.append({
                'index': input_index,
                'stream_index': i,
                'language': audio.get('language', 'und'),
                'default': audio.get('default', False),
                'forced': audio.get('forced', False)
            })
            input_index += 1
    
    # Add subtitle inputs
    subtitle_map_info = []
    if subtitles:
        for i, subtitle in enumerate(subtitles):
            ffmpeg_cmd += ["-i", subtitle['file']]
            subtitle_map_info.append({
                'index': input_index,
                'stream_index': i,
                'language': subtitle.get('language', 'und'),
                'default': subtitle.get('default', False),
                'forced': subtitle.get('forced', False)
            })
            input_index += 1

    # Map video stream (copy as-is)
    ffmpeg_cmd += ["-map", "0:v", "-c:v", "copy"]
    
    # Map audio streams
    if audio_tracks:
        for audio_info in audio_map_info:
            ffmpeg_cmd += ["-map", f"{audio_info['index']}:a"]
        ffmpeg_cmd += ["-c:a", "copy"]
        # Add metadata for each audio stream
        for i, audio_info in enumerate(audio_map_info):
            ffmpeg_cmd += [f"-metadata:s:a:{i}", f"language={audio_info['language']}"]
            disposition = []
            if audio_info['default']:
                disposition.append("default")
            if audio_info['forced']:
                disposition.append("forced")
            if disposition:
                ffmpeg_cmd += [f"-disposition:a:{i}", "+".join(disposition)]
    else:
        # Keep original audio
        ffmpeg_cmd += ["-map", "0:a", "-c:a", "copy"]
    
    # Map subtitle streams
    if subtitles:
        for subtitle_info in subtitle_map_info:
            ffmpeg_cmd += ["-map", f"{subtitle_info['index']}"]
        ffmpeg_cmd += ["-c:s", "mov_text"]
        for i, subtitle_info in enumerate(subtitle_map_info):
            ffmpeg_cmd += [f"-metadata:s:s:{i}", f"language={subtitle_info['language']}"]
            disposition = []
            if subtitle_info['default']:
                disposition.append("default")
            if subtitle_info['forced']:
                disposition.append("forced")
            if disposition:
                ffmpeg_cmd += [f"-disposition:s:{i}", "+".join(disposition)]

    # Global flags and output
    ffmpeg_cmd += [
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-movflags", "+faststart",
        output_file
    ]

    print("Running FFmpeg (Add Subtitles/Audio):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Adding subtitles/audio failed!", file=sys.stderr)
        sys.exit(1)


def remove_all_subtitles(input_file, output_file):
    """
    Remove all subtitle tracks from video file.
    
    Args:
        input_file: Path to input video file
        output_file: Path to output video file
    """
    print(f"Removing all subtitles: {input_file} -> {output_file}")

    ffmpeg_cmd = [
        "ffmpeg", "-threads", "0", "-i", input_file,
        "-map", "0:v", "-c:v", "copy",
        "-map", "0:a", "-c:a", "copy",
        "-sn",  # Remove all subtitle streams
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-movflags", "+faststart",
        output_file
    ]

    print("Running FFmpeg (Remove Subtitles):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Removing subtitles failed!", file=sys.stderr)
        sys.exit(1)


def remove_all_audio(input_file, output_file):
    """
    Remove all audio tracks from video file.
    
    Args:
        input_file: Path to input video file
        output_file: Path to output video file
    """
    print(f"Removing all audio: {input_file} -> {output_file}")

    ffmpeg_cmd = [
        "ffmpeg", "-threads", "0", "-i", input_file,
        "-map", "0:v", "-c:v", "copy",
        "-an",  # Remove all audio streams
        "-map", "0:s?", "-c:s", "copy",  # Keep subtitles if they exist
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-movflags", "+faststart",
        output_file
    ]

    print("Running FFmpeg (Remove Audio):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Removing audio failed!", file=sys.stderr)
        sys.exit(1)


def extract_all_subtitles(input_file, output_dir=None):
    """
    Extract all subtitle tracks from video file.
    
    Args:
        input_file: Path to input video file
        output_dir: Directory to save extracted subtitles (optional, defaults to same dir as input)
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_file) or "."
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print(f"Extracting all subtitles from: {input_file}")

    # First, get info about subtitle streams
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "csv", "-show_streams",
        "-select_streams", "s", input_file
    ]
    
    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        subtitle_streams = probe_result.stdout.strip().split('\n') if probe_result.stdout.strip() else []
    except subprocess.CalledProcessError:
        print("No subtitle streams found or error probing file")
        return

    if not subtitle_streams:
        print("No subtitle streams found in the video")
        return

    # Extract each subtitle stream
    for i, stream_info in enumerate(subtitle_streams):
        if stream_info:  # Skip empty lines
            output_file = os.path.join(output_dir, f"{base_name}_subtitle_{i}.srt")
            
            ffmpeg_cmd = [
                "ffmpeg", "-i", input_file,
                "-map", f"0:s:{i}",
                "-c:s", "srt",
                "-y",  # Overwrite output files
                output_file
            ]
            
            print(f"Extracting subtitle track {i}: {output_file}")
            process = subprocess.run(ffmpeg_cmd)
            
            if process.returncode == 0:
                print(f"Successfully extracted: {output_file}")
            else:
                print(f"Failed to extract subtitle track {i}")


def extract_all_audio(input_file, output_dir=None, format="m4a"):
    """
    Extract all audio tracks from video file.
    
    Args:
        input_file: Path to input video file
        output_dir: Directory to save extracted audio (optional, defaults to same dir as input)
        format: Output audio format (m4a, mp3, wav, etc.)
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_file) or "."
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print(f"Extracting all audio tracks from: {input_file}")

    # First, get info about audio streams
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "csv", "-show_streams",
        "-select_streams", "a", input_file
    ]
    
    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        audio_streams = probe_result.stdout.strip().split('\n') if probe_result.stdout.strip() else []
    except subprocess.CalledProcessError:
        print("No audio streams found or error probing file")
        return

    if not audio_streams:
        print("No audio streams found in the video")
        return

    # Extract each audio stream
    for i, stream_info in enumerate(audio_streams):
        if stream_info:  # Skip empty lines
            output_file = os.path.join(output_dir, f"{base_name}_audio_{i}.{format}")
            
            ffmpeg_cmd = [
                "ffmpeg", "-i", input_file,
                "-map", f"0:a:{i}",
                "-c:a", "copy" if format == "m4a" else "aac",
                "-y",  # Overwrite output files
                output_file
            ]
            
            print(f"Extracting audio track {i}: {output_file}")
            process = subprocess.run(ffmpeg_cmd)
            
            if process.returncode == 0:
                print(f"Successfully extracted: {output_file}")
            else:
                print(f"Failed to extract audio track {i}")


def extract_specific_subtitle(input_file, subtitle_index, output_file, format="srt"):
    """
    Extract a specific subtitle track from video file.
    
    Args:
        input_file: Path to input video file
        subtitle_index: Index of subtitle track to extract (0-based)
        output_file: Path for output subtitle file
        format: Output subtitle format (srt, vtt, ass, etc.)
    """
    print(f"Extracting subtitle track {subtitle_index}: {input_file} -> {output_file}")

    ffmpeg_cmd = [
        "ffmpeg", "-i", input_file,
        "-map", f"0:s:{subtitle_index}",
        "-c:s", format,
        "-y",  # Overwrite output files
        output_file
    ]

    print("Running FFmpeg (Extract Subtitle):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print(f"Error: Failed to extract subtitle track {subtitle_index}!", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Successfully extracted subtitle: {output_file}")


def extract_specific_audio(input_file, audio_index, output_file, format="m4a"):
    """
    Extract a specific audio track from video file.
    
    Args:
        input_file: Path to input video file
        audio_index: Index of audio track to extract (0-based)
        output_file: Path for output audio file
        format: Output audio format (m4a, mp3, wav, etc.)
    """
    print(f"Extracting audio track {audio_index}: {input_file} -> {output_file}")

    # Choose codec based on format
    codec = "copy" if format == "m4a" else "aac"
    
    ffmpeg_cmd = [
        "ffmpeg", "-i", input_file,
        "-map", f"0:a:{audio_index}",
        "-c:a", codec,
        "-y",  # Overwrite output files
        output_file
    ]

    print("Running FFmpeg (Extract Audio):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print(f"Error: Failed to extract audio track {audio_index}!", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Successfully extracted audio: {output_file}")


def get_stream_info(input_file):
    """
    Get detailed stream information including language metadata.
    
    Args:
        input_file: Path to input video file
    
    Returns:
        dict: Contains 'audio' and 'subtitle' lists with stream info
    """
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", input_file
    ]
    
    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        stream_data = json.loads(probe_result.stdout)
        
        audio_streams = []
        subtitle_streams = []
        
        for i, stream in enumerate(stream_data.get('streams', [])):
            if stream['codec_type'] == 'audio':
                language = stream.get('tags', {}).get('language', 'und')
                audio_streams.append({
                    'index': len(audio_streams),  # Audio stream index
                    'global_index': i,  # Global stream index
                    'language': language,
                    'codec': stream.get('codec_name', 'unknown')
                })
            elif stream['codec_type'] == 'subtitle':
                language = stream.get('tags', {}).get('language', 'und')
                subtitle_streams.append({
                    'index': len(subtitle_streams),  # Subtitle stream index
                    'global_index': i,  # Global stream index
                    'language': language,
                    'codec': stream.get('codec_name', 'unknown')
                })
        
        return {'audio': audio_streams, 'subtitle': subtitle_streams}
    
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error getting stream info: {e}")
        return {'audio': [], 'subtitle': []}


def extract_audio_by_language(input_file, language_code, output_dir=None, format="m4a"):
    """
    Extract audio tracks by language code.
    
    Args:
        input_file: Path to input video file
        language_code: 3-letter language code (e.g., 'ara', 'eng', 'fra')
        output_dir: Directory to save extracted audio (optional)
        format: Output audio format (m4a, mp3, wav, etc.)
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_file) or "."
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print(f"Extracting {language_code} audio tracks from: {input_file}")

    # Get stream information
    stream_info = get_stream_info(input_file)
    audio_streams = stream_info['audio']
    
    if not audio_streams:
        print("No audio streams found in the video")
        return
    
    # Find matching language streams
    matching_streams = [stream for stream in audio_streams if stream['language'] == language_code]
    
    if not matching_streams:
        print(f"No audio tracks found for language: {language_code}")
        print("Available languages:")
        for stream in audio_streams:
            print(f"  - Track {stream['index']}: {stream['language']} ({stream['codec']})")
        return
    
    # Extract each matching stream
    for stream in matching_streams:
        output_file = os.path.join(output_dir, f"{base_name}_{language_code}_audio_{stream['index']}.{format}")
        
        # Choose codec based on format
        codec = "copy" if format == "m4a" else "aac"
        
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-map", f"0:a:{stream['index']}",
            "-c:a", codec,
            "-y",  # Overwrite output files
            output_file
        ]
        
        print(f"Extracting {language_code} audio track {stream['index']}: {output_file}")
        process = subprocess.run(ffmpeg_cmd)
        
        if process.returncode == 0:
            print(f"Successfully extracted: {output_file}")
        else:
            print(f"Failed to extract {language_code} audio track {stream['index']}")


def extract_subtitle_by_language(input_file, language_code, output_dir=None, format="srt"):
    """
    Extract subtitle tracks by language code.
    
    Args:
        input_file: Path to input video file
        language_code: 3-letter language code (e.g., 'ara', 'eng', 'fra')
        output_dir: Directory to save extracted subtitles (optional)
        format: Output subtitle format (srt, vtt, ass, etc.)
    """
    if output_dir is None:
        output_dir = os.path.dirname(input_file) or "."
    
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    print(f"Extracting {language_code} subtitle tracks from: {input_file}")

    # Get stream information
    stream_info = get_stream_info(input_file)
    subtitle_streams = stream_info['subtitle']
    
    if not subtitle_streams:
        print("No subtitle streams found in the video")
        return
    
    # Find matching language streams
    matching_streams = [stream for stream in subtitle_streams if stream['language'] == language_code]
    
    if not matching_streams:
        print(f"No subtitle tracks found for language: {language_code}")
        print("Available languages:")
        for stream in subtitle_streams:
            print(f"  - Track {stream['index']}: {stream['language']} ({stream['codec']})")
        return
    
    # Extract each matching stream
    for stream in matching_streams:
        output_file = os.path.join(output_dir, f"{base_name}_{language_code}_subtitle_{stream['index']}.{format}")
        
        ffmpeg_cmd = [
            "ffmpeg", "-i", input_file,
            "-map", f"0:s:{stream['index']}",
            "-c:s", format,
            "-y",  # Overwrite output files
            output_file
        ]
        
        print(f"Extracting {language_code} subtitle track {stream['index']}: {output_file}")
        process = subprocess.run(ffmpeg_cmd)
        
        if process.returncode == 0:
            print(f"Successfully extracted: {output_file}")
        else:
            print(f"Failed to extract {language_code} subtitle track {stream['index']}")


def list_available_languages(input_file):
    """
    List all available audio and subtitle languages in the video file.
    
    Args:
        input_file: Path to input video file
    """
    print(f"Analyzing languages in: {input_file}")
    
    stream_info = get_stream_info(input_file)
    
    print("\n=== AUDIO TRACKS ===")
    if stream_info['audio']:
        for stream in stream_info['audio']:
            print(f"Track {stream['index']}: {stream['language']} ({stream['codec']})")
    else:
        print("No audio tracks found")
    
    print("\n=== SUBTITLE TRACKS ===")
    if stream_info['subtitle']:
        for stream in stream_info['subtitle']:
            print(f"Track {stream['index']}: {stream['language']} ({stream['codec']})")
    else:
        print("No subtitle tracks found")
    
    print()


def extract_multiple_languages_audio(input_file, language_codes, output_dir=None, format="m4a"):
    """
    Extract audio tracks for multiple languages at once.
    
    Args:
        input_file: Path to input video file
        language_codes: List of 3-letter language codes (e.g., ['ara', 'eng', 'fra'])
        output_dir: Directory to save extracted audio (optional)
        format: Output audio format (m4a, mp3, wav, etc.)
    """
    print(f"Extracting multiple language audio tracks: {language_codes}")
    
    for lang_code in language_codes:
        print(f"\n--- Processing {lang_code} ---")
        extract_audio_by_language(input_file, lang_code, output_dir, format)


def extract_multiple_languages_subtitle(input_file, language_codes, output_dir=None, format="srt"):
    """
    Extract subtitle tracks for multiple languages at once.
    
    Args:
        input_file: Path to input video file
        language_codes: List of 3-letter language codes (e.g., ['ara', 'eng', 'fra'])
        output_dir: Directory to save extracted subtitles (optional)
        format: Output subtitle format (srt, vtt, ass, etc.)
    """
    print(f"Extracting multiple language subtitle tracks: {language_codes}")
    
    for lang_code in language_codes:
        print(f"\n--- Processing {lang_code} ---")
        extract_subtitle_by_language(input_file, lang_code, output_dir, format)



def remove_all_metadata(input_file, output_file, keep_chapters=False):
    """
    Remove all metadata from video file while keeping streams intact.
    
    Args:
        input_file: Path to input video file
        output_file: Path to output video file
        keep_chapters: Whether to keep chapter information (default: False)
    """
    print(f"Removing all metadata: {input_file} -> {output_file}")

    ffmpeg_cmd = [
        "ffmpeg", "-threads", "0", "-i", input_file,
        "-map", "0",  # Map all streams
        "-c", "copy",  # Copy all streams without re-encoding
        "-map_metadata", "-1",  # Remove all metadata
    ]
    
    # Handle chapters
    if keep_chapters:
        ffmpeg_cmd += ["-map_chapters", "0"]  # Keep chapters
    else:
        ffmpeg_cmd += ["-map_chapters", "-1"]  # Remove chapters
    
    # Remove all stream-level metadata
    ffmpeg_cmd += [
        "-fflags", "+bitexact",  # Remove encoder info
        "-movflags", "+faststart",
        output_file
    ]

    print("Running FFmpeg (Remove Metadata):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Removing metadata failed!", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Successfully removed metadata: {output_file}")

def view_metadata(input_file):
    """
    Display all metadata information in the video file.
    
    Args:
        input_file: Path to input video file
    """
    print(f"Analyzing metadata in: {input_file}")
    
    # Get global metadata
    probe_cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json", 
        "-show_format", "-show_streams", "-show_chapters", input_file
    ]
    
    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(probe_result.stdout)
        
        # Show global metadata
        print("\n=== GLOBAL METADATA ===")
        format_tags = metadata.get('format', {}).get('tags', {})
        if format_tags:
            for key, value in format_tags.items():
                print(f"{key}: {value}")
        else:
            print("No global metadata found")
        
        # Show stream metadata
        print("\n=== STREAM METADATA ===")
        for i, stream in enumerate(metadata.get('streams', [])):
            stream_type = stream.get('codec_type', 'unknown')
            codec_name = stream.get('codec_name', 'unknown')
            print(f"\nStream {i} ({stream_type} - {codec_name}):")
            
            stream_tags = stream.get('tags', {})
            if stream_tags:
                for key, value in stream_tags.items():
                    print(f"  {key}: {value}")
            else:
                print("  No metadata")
        
        # Show chapters
        print("\n=== CHAPTERS ===")
        chapters = metadata.get('chapters', [])
        if chapters:
            for i, chapter in enumerate(chapters):
                title = chapter.get('tags', {}).get('title', f'Chapter {i+1}')
                start = chapter.get('start_time', '0')
                end = chapter.get('end_time', '0')
                print(f"Chapter {i+1}: {title} ({start}s - {end}s)")
        else:
            print("No chapters found")
            
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error reading metadata: {e}")


def remove_metadata_keep_language_tags(input_file, output_file, keep_chapters=False):
    """
    Remove metadata but keep language tags for audio/subtitle streams.
    
    Args:
        input_file: Path to input video file
        output_file: Path to output video file
        keep_chapters: Whether to keep chapter information (default: False)
    """
    print(f"Removing metadata (keeping language tags): {input_file} -> {output_file}")

    # Get stream info to preserve language tags
    stream_info = get_stream_info(input_file)
    
    ffmpeg_cmd = [
        "ffmpeg", "-threads", "0", "-i", input_file,
        "-map", "0",  # Map all streams
        "-c", "copy",  # Copy all streams without re-encoding
        "-map_metadata", "-1",  # Remove all global metadata
    ]
    
    # Handle chapters
    if keep_chapters:
        ffmpeg_cmd += ["-map_chapters", "0"]
    else:
        ffmpeg_cmd += ["-map_chapters", "-1"]
    
    # Re-add language metadata for audio streams
    for stream in stream_info['audio']:
        if stream['language'] != 'und':  # Only add if language is known
            ffmpeg_cmd += [f"-metadata:s:a:{stream['index']}", f"language={stream['language']}"]
    
    # Re-add language metadata for subtitle streams
    for stream in stream_info['subtitle']:
        if stream['language'] != 'und':  # Only add if language is known
            ffmpeg_cmd += [f"-metadata:s:s:{stream['index']}", f"language={stream['language']}"]
    
    ffmpeg_cmd += [
        "-fflags", "+bitexact",
        "-movflags", "+faststart",
        output_file
    ]

    print("Running FFmpeg (Remove Metadata - Keep Languages):\n" + " ".join(ffmpeg_cmd))
    process = subprocess.run(ffmpeg_cmd)
    if process.returncode != 0:
        print("Error: Removing metadata failed!", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Successfully removed metadata (kept language tags): {output_file}")

def get_media_info(file_path):
    # Run ffprobe command to get video and audio info in JSON format
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-print_format', 'json', 
        '-show_streams', 
        '-show_format', 
        file_path
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    
    # Parse the output JSON
    media_info = json.loads(result.stdout)
    
    video_info = None
    audio_info = None

    # Find the video and audio streams
    for stream in media_info['streams']:
        if stream['codec_type'] == 'video':
            video_info = stream
        elif stream['codec_type'] == 'audio':
            audio_info = stream
    
    return video_info, audio_info, media_info['format']

def check_bitrate_type(bitrate):
    # Simple heuristic to determine if bitrate is constant or variable
    if bitrate:
        return "CBR"  # If we have a bitrate, we'll assume it's CBR
    else:
        return "VBR"  # If no constant bitrate is found, it's likely VBR
    
def convert_to_hls_multiple_variants(input_paths, output_dir):
    """
    Convert multiple MP4 files to a single HLS master playlist using Bento4.
    Cleans up I-frame playlists and removes Bento4 version comment.
    """
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "/home/kda/uploader/encode/Bento4-SDK-1-6-0-641.x86_64-unknown-linux/bin/mp4hls",
        "--output-dir=" + output_dir,
        "--segment-duration=8",
        "--force"
    ] + input_paths

    subprocess.run(cmd, check=True)

    # Clean up I-frame playlists and version comment
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if "iframes.m3u8" in file:
                os.remove(os.path.join(root, file))

    # Edit master.m3u8
    master_playlist = os.path.join(output_dir, "master.m3u8")
    if os.path.exists(master_playlist):
        with open(master_playlist, "r") as f:
            lines = f.readlines()
        with open(master_playlist, "w") as f:
            for line in lines:
                if "I-FRAME-STREAM-INF" in line:
                    continue
                if line.startswith("# Created with Bento4 mp4-hls.py"):
                    continue
                f.write(line)

    # Remove iframe files from inside media-* folders
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith("iframes.m3u8"):
                os.remove(os.path.join(root, file))
                
if __name__ == "__main__":
    encode_video_with_soft_tracks(
        input_file='input.mp4',
        output_file='/home/kda/decrypt/final.mp4',
        font_path='/path/to/font.ttf',
        text='Sample Text',
        x=10,
        y=10,
        fontsize=24,
        fontcolor='white',
        bitrate='2000k',
        audio_bitrate='128k',
        maxrate='2500k',
        bufsize='4000k',
        pix_fmt='yuv420p',
        sample_rate=48000,
        resolution='1920x1080',
        audio_tracks=[
            {'file': 'arabic.m4a', 'language': 'ara', 'default': True, 'forced': True},
            {'file': 'english.m4a', 'language': 'eng', 'default': False, 'forced': False},
            {'file': 'french.m4a', 'language': 'fra', 'default': False, 'forced': False}
        ],
        subtitles=[
            {'file': 'arabic.vtt', 'language': 'ara', 'default': True, 'forced': True},
            {'file': 'english.vtt', 'language': 'eng', 'default': False, 'forced': False},
            {'file': 'french.vtt', 'language': 'fra', 'default': False, 'forced': False}
        ]
    )


    add_subtitles_and_audio_only(
        input_file='input.mp4',
        output_file='/home/kda/decrypt/with_tracks.mp4',
        audio_tracks=[
            {'file': 'arabic.m4a', 'language': 'ara', 'default': True, 'forced': False},
            {'file': 'english.m4a', 'language': 'eng', 'default': False, 'forced': False}
        ],
        subtitles=[
            {'file': 'arabic.srt', 'language': 'ara', 'default': True, 'forced': False},
            {'file': 'english.srt', 'language': 'eng', 'default': False, 'forced': False}
        ]
    )

    remove_all_subtitles(
        input_file='input_with_subtitles.mp4',
        output_file='/home/kda/decrypt/no_subtitles.mp4'
    )

    # Example 4: Remove all audio
    remove_all_audio(
        input_file='input_with_audio.mp4',
        output_file='/home/kda/decrypt/no_audio.mp4'
    )

    # Example 5: Extract all subtitles from video
    extract_all_subtitles(
        input_file='input.mp4',
        output_dir='/home/kda/decrypt/extracted_subs'
    )

    # Example 6: Extract all audio tracks from video
    extract_all_audio(
        input_file='input.mp4',
        output_dir='/home/kda/decrypt/extracted_audio',
        format='m4a'  # or 'mp3', 'wav', etc.
    )

    # Example 7: Extract specific subtitle track (index 0 = first subtitle)
    extract_specific_subtitle(
        input_file='input.mp4',
        subtitle_index=0,
        output_file='/home/kda/decrypt/arabic_subtitle.srt',
        format='srt'  # or 'vtt', 'ass', etc.
    )

    # Example 8: Extract specific audio track (index 1 = second audio track)
    extract_specific_audio(
        input_file='input.mp4',
        audio_index=1,
        output_file='/home/kda/decrypt/english_audio.m4a',
        format='m4a'  # or 'mp3', 'wav', etc.
    )

    # Example 9: Burn mode with logo and subtitle
    encode_video_with_burn(
        input_file='input.mp4',
        output_file='/home/kda/decrypt/burned.mp4',
        font_path='/path/to/font.ttf',
        text='Watermark Text',
        x=10,
        y=10,
        fontsize=24,
        fontcolor='yellow',
        bitrate='2000k',
        audio_bitrate='128k',
        maxrate='2500k',
        bufsize='4000k',
        pix_fmt='yuv420p',
        sample_rate=48000,
        resolution='1920x1080',
        burn_subtitle='arabic.srt',
        logo_path='logo.png',
        logo_x=10,
        logo_y=10,
        logo_scale='100:100',
        audio_file='replacement_audio.m4a',
        audio_lang='ara'
    )
    


    extract_audio_by_language(
        input_file='input.mp4',
        language_code='ara',
        output_dir='/home/kda/decrypt/extracted_audio',
        format='m4a'
    )
    
    # Example 3: Extract English subtitle tracks only
    extract_subtitle_by_language(
        input_file='input.mp4',
        language_code='eng',
        output_dir='/home/kda/decrypt/extracted_subs',
        format='srt'
    )
    
    # Example 4: Extract French audio tracks only
    extract_audio_by_language(
        input_file='input.mp4',
        language_code='fra',
        output_dir='/home/kda/decrypt/extracted_audio',
        format='mp3'
    )
    
    # Example 5: Extract multiple language audio tracks at once
    extract_multiple_languages_audio(
        input_file='input.mp4',
        language_codes=['ara', 'eng', 'fra'],
        output_dir='/home/kda/decrypt/all_audio',
        format='m4a'
    )
    
    # Example 6: Extract multiple language subtitle tracks at once
    extract_multiple_languages_subtitle(
        input_file='input.mp4',
        language_codes=['ara', 'eng', 'fra'],
        output_dir='/home/kda/decrypt/all_subs',
        format='srt'
    )
    
    # Example 7: Extract Spanish subtitles (if available)
    extract_subtitle_by_language(
        input_file='input.mp4',
        language_code='spa',
        output_dir='/home/kda/decrypt/spanish',
        format='vtt'
    )
    
    # Example 8: Extract German audio (if available)
    extract_audio_by_language(
        input_file='input.mp4',
        language_code='deu',
        output_dir='/home/kda/decrypt/german',
        format='wav'
    )

    view_metadata('input.mp4')

    remove_all_metadata(
        input_file='input.mp4',
        output_file='/home/kda/decrypt/no_metadata.mp4',
        keep_chapters=False
    )

    remove_metadata_keep_language_tags(
    input_file='/home/kda/decrypt/output.mp4',
    output_file='/home/kda/uploader/ss.mp4',
    keep_chapters=True
    )
    
    get_media_info('/home/kda/decrypt/output.mp4')