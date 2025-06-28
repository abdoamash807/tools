import subprocess
import sys
import os

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





if __name__ == "__main__":
    encode_video_with_soft_tracks(
        input_file='input.mp4',
        output_file='/home/kda/decrypt/final.mp4',
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