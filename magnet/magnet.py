import libtorrent as lt
import time
import re
import os
import argparse
import json
import sys

async def estimate_duration_from_filename(filename):
    """
    Enhanced duration estimation with more patterns and better accuracy
    """
    filename_lower = filename.lower()
    
    # TV Show patterns with more comprehensive matching
    tv_patterns = [
        (r's(\d+)e(\d+)', lambda m: get_tv_duration(int(m.group(1)), int(m.group(2)))),
        (r'season\s*(\d+).*episode\s*(\d+)', lambda m: get_tv_duration(int(m.group(1)), int(m.group(2)))),
        (r'(\d+)x(\d{2,})', lambda m: get_tv_duration(int(m.group(1)), int(m.group(2)))),
        (r'e(\d+)', lambda m: 45 * 60),  # Simple episode pattern
    ]
    
    for pattern, duration_func in tv_patterns:
        match = re.search(pattern, filename_lower)
        if match:
            return duration_func(match)
    
    # Movie year patterns (more reliable movie indicator)
    if re.search(r'\b(19[2-9]\d|20[0-4]\d)\b', filename_lower):
        # Check for movie length indicators
        if any(term in filename_lower for term in ['extended', 'director', 'uncut', 'ultimate']):
            return 150 * 60  # Extended cuts are longer
        return 110 * 60  # Standard movie length
    
    # Quality-based hints for content type
    if any(indicator in filename_lower for indicator in ['bluray', 'bdrip', 'dvdrip', 'webrip', 'web-dl']):
        return 110 * 60  # Movies
    
    # Default fallback
    return 60 * 60

def get_tv_duration(season, episode):
    """
    Get TV episode duration based on season/episode patterns
    """
    # Pilot episodes and finales are often longer
    if episode == 1 and season == 1:  # Pilot
        return 50 * 60
    elif episode >= 20:  # Likely finale
        return 50 * 60
    else:
        return 42 * 60  # Standard TV episode (without commercials)

def get_encoding_profile_bitrate(filename, quality):
    """
    More accurate bitrate estimation based on encoding profiles and groups
    """
    filename_lower = filename.lower()
    
    # Group-specific encoding profiles (more accurate)
    group_profiles = {
        'yts': {
            '1080p': {'video': 1800, 'audio': 128},  # YTS is very efficient
            '720p': {'video': 900, 'audio': 128},
        },
        'rarbg': {
            '1080p': {'video': 2500, 'audio': 256},
            '720p': {'video': 1500, 'audio': 192},
        },
        'ettv': {
            '1080p': {'video': 3000, 'audio': 224},
            '720p': {'video': 1800, 'audio': 192},
        },
        'sparks': {
            '1080p': {'video': 4000, 'audio': 320},  # Higher quality
            '720p': {'video': 2500, 'audio': 256},
        },
        'web-dl': {
            '1080p': {'video': 5000, 'audio': 320},  # High quality web rips
            '720p': {'video': 3000, 'audio': 256},
        }
    }
    
    # Detect group
    detected_profile = None
    for group in group_profiles:
        if group in filename_lower:
            detected_profile = group_profiles[group]
            break
    
    # Web-DL/WEBRip special handling
    if not detected_profile and ('web-dl' in filename_lower or 'webrip' in filename_lower):
        detected_profile = group_profiles['web-dl']
    
    # Default profiles if no group detected
    if not detected_profile:
        detected_profile = {
            '1080p': {'video': 2800, 'audio': 192},
            '720p': {'video': 1600, 'audio': 128},
            '480p': {'video': 1000, 'audio': 128},
            '360p': {'video': 600, 'audio': 96},
        }
    
    return detected_profile.get(quality, {'video': 2000, 'audio': 128})

def estimate_duration_from_size_and_encoding(file_size_bytes, filename, manual_duration=None):
    """
    Most accurate duration estimation using realistic encoding profiles
    """
    if manual_duration:
        return manual_duration * 60
    
    filename_lower = filename.lower()
    size_mb = file_size_bytes / (1024 * 1024)
    
    # Detect quality
    quality = detect_quality(filename)
    
    # Get realistic bitrate profile for this encoding
    bitrate_profile = get_encoding_profile_bitrate(filename, quality)
    total_bitrate_kbps = bitrate_profile['video'] + bitrate_profile['audio']
    
    # Calculate duration: (file_size_MB * 8 * 1024) / (bitrate_kbps * 60)
    estimated_duration_minutes = (size_mb * 8 * 1024) / (total_bitrate_kbps * 60)
    
    # Content-aware duration constraints
    content_type = detect_content_type(filename)
    
    if content_type == 'TV Episode':
        # TV episodes: 18-75 minutes (accounting for various show formats)
        estimated_duration_minutes = max(18, min(75, estimated_duration_minutes))
    else:  # Movie
        # Movies: 70-210 minutes (wider range for different movie types)
        if 'short' in filename_lower:
            estimated_duration_minutes = max(5, min(40, estimated_duration_minutes))
        else:
            estimated_duration_minutes = max(70, min(210, estimated_duration_minutes))
    
    return int(estimated_duration_minutes * 60)

def detect_hdr_and_codec(filename):
    """
    Detect HDR and codec information for more accurate bitrate estimation
    """
    filename_lower = filename.lower()
    
    hdr_formats = []
    if 'hdr10' in filename_lower:
        hdr_formats.append('HDR10')
    if 'dolby vision' in filename_lower or 'dv' in filename_lower:
        hdr_formats.append('Dolby Vision')
    if 'hdr' in filename_lower and not hdr_formats:
        hdr_formats.append('HDR')
    
    codecs = []
    codec_patterns = {
        'h264': r'h\.?264|x264|avc',
        'h265': r'h\.?265|x265|hevc',
        'av1': r'av1',
        'vp9': r'vp9'
    }
    
    for codec, pattern in codec_patterns.items():
        if re.search(pattern, filename_lower):
            codecs.append(codec.upper())
    
    return {
        'hdr_formats': hdr_formats,
        'video_codecs': codecs,
        'has_hdr': len(hdr_formats) > 0,
        'is_modern_codec': any(codec in ['h265', 'av1', 'vp9'] for codec in [c.lower() for c in codecs])
    }

def calculate_confidence_score(filename, file_size, estimated_duration):
    """
    Calculate confidence score for the estimation
    """
    confidence = 0.5  # Base confidence
    filename_lower = filename.lower()
    
    # Increase confidence for known groups
    known_groups = ['yts', 'rarbg', 'ettv', 'sparks', 'eztv']
    if any(group in filename_lower for group in known_groups):
        confidence += 0.2
    
    # Increase confidence for clear quality indicators
    if any(qual in filename_lower for qual in ['1080p', '720p', '480p']):
        confidence += 0.15
    
    # Increase confidence for codec information
    codec_info = detect_hdr_and_codec(filename)
    if codec_info['video_codecs']:
        confidence += 0.1
    
    # Decrease confidence for very small or very large files (likely incomplete or remux)
    size_gb = file_size / (1024**3)
    if size_gb < 0.3 or size_gb > 50:
        confidence -= 0.2
    
    # Increase confidence for reasonable duration estimates
    duration_hours = estimated_duration / 3600
    if 0.3 <= duration_hours <= 4:  # Reasonable range
        confidence += 0.1
    
    return min(1.0, max(0.1, confidence))

def get_torrent_info_from_magnet(magnet_uri, manual_duration=None, progress_callback=None):
    """
    Enhanced torrent analysis with improved accuracy and optional progress callback
    """
    ses = lt.session()
    
    # Modern session settings
    settings = ses.get_settings()
    settings['listen_interfaces'] = '0.0.0.0:6881'
    settings['enable_dht'] = True
    settings['enable_lsd'] = True
    settings['enable_upnp'] = True
    settings['enable_natpmp'] = True
    ses.apply_settings(settings)
    
    # Add torrent
    params = lt.add_torrent_params()
    params.url = magnet_uri
    params.save_path = './temp_download'
    params.storage_mode = lt.storage_mode_t.storage_mode_sparse
    
    if progress_callback:
        progress_callback("Adding magnet link...")
    
    handle = ses.add_torrent(params)
    
    if progress_callback:
        progress_callback("Fetching metadata...")
    
    timeout = 30  # 30 second timeout
    start_time = time.time()
    
    while not handle.status().has_metadata:
        if time.time() - start_time > timeout:
            raise Exception("Timeout: Could not fetch metadata within 30 seconds")
        time.sleep(1)
    
    torinfo = handle.torrent_file()
    files = torinfo.files()
    
    # Get all files with detailed analysis
    file_list = []
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.m2ts', '.ts'}
    
    for i in range(files.num_files()):
        file_path = files.file_path(i)
        file_size = files.file_size(i)
        _, ext = os.path.splitext(file_path)
        
        file_info = {
            'index': i,
            'path': file_path,
            'size': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'is_video': ext.lower() in video_extensions,
            'extension': ext.lower()
        }
        file_list.append(file_info)
    
    # Find the main video file (largest video file)
    video_files = [f for f in file_list if f['is_video']]
    if not video_files:
        raise Exception("No video files found in torrent")
    
    main_video = max(video_files, key=lambda f: f['size'])
    
    # Enhanced duration estimation
    duration_seconds = estimate_duration_from_size_and_encoding(
        main_video['size'], main_video['path'], manual_duration
    )
    
    # Calculate accurate bitrates
    total_bitrate_kbps = (main_video['size'] * 8) / (duration_seconds * 1000)
    
    # Get encoding profile for more accurate breakdown
    quality = detect_quality(main_video['path'])
    bitrate_profile = get_encoding_profile_bitrate(main_video['path'], quality)
    
    # Use profile ratios for more accurate video/audio split
    profile_total = bitrate_profile['video'] + bitrate_profile['audio']
    video_ratio = bitrate_profile['video'] / profile_total
    audio_ratio = bitrate_profile['audio'] / profile_total
    
    estimated_video_bitrate = total_bitrate_kbps * video_ratio
    estimated_audio_bitrate = total_bitrate_kbps * audio_ratio
    
    # Additional analysis
    codec_info = detect_hdr_and_codec(main_video['path'])
    confidence = calculate_confidence_score(main_video['path'], main_video['size'], duration_seconds)
    
    # Calculate total sizes
    total_video_size = sum(f['size'] for f in video_files)
    
    return {
        'status': 'success',
        'torrent_name': torinfo.name(),
        'main_video_file': main_video['path'],
        'file_size_MB': main_video['size_mb'],
        'file_size_GB': round(main_video['size'] / (1024**3), 3),
        'estimated_duration_minutes': round(duration_seconds / 60, 1),
        'estimated_duration_hours': round(duration_seconds / 3600, 2),
        'total_bitrate_kbps': round(total_bitrate_kbps, 1),
        'total_bitrate_mbps': round(total_bitrate_kbps / 1000, 2),
        'estimated_video_bitrate_kbps': round(estimated_video_bitrate, 1),
        'estimated_audio_bitrate_kbps': round(estimated_audio_bitrate, 1),
        'confidence_score': round(confidence, 2),
        'confidence_label': get_confidence_label(confidence),
        'quality_detected': quality,
        'content_type': detect_content_type(main_video['path']),
        'encoding_group': detect_encoding_group(main_video['path']),
        'codec_info': codec_info,
        'total_files': len(file_list),
        'video_files_count': len(video_files),
        'total_video_size_gb': round(total_video_size / (1024**3), 3),
        'all_video_files': [
            {
                'name': os.path.basename(vf['path']),
                'size_mb': vf['size_mb'],
                'size_gb': round(vf['size'] / (1024**3), 3)
            }
            for vf in video_files
        ],
        'estimation_method': 'Enhanced encoding profile analysis',
        'manual_duration_used': manual_duration is not None,
        'analysis_timestamp': time.time()
    }

def detect_quality(filename):
    """Enhanced quality detection"""
    filename_lower = filename.lower()
    
    # More comprehensive quality patterns
    quality_patterns = [
        ('2160p', '4K/UHD'),
        ('1440p', '1440p'),
        ('1080p', '1080p'),
        ('720p', '720p'),
        ('480p', '480p'),
        ('360p', '360p'),
        ('240p', '240p'),
    ]
    
    for pattern, quality in quality_patterns:
        if pattern in filename_lower:
            return quality
    
    # Fallback detection
    if any(term in filename_lower for term in ['uhd', '4k']):
        return '4K/UHD'
    elif any(term in filename_lower for term in ['hd', 'bluray', 'bdrip']):
        return '1080p (assumed)'
    
    return 'Unknown'

def detect_encoding_group(filename):
    """Enhanced encoding group detection"""
    filename_lower = filename.lower()
    
    group_info = {
        'yts': 'YTS (Efficient encoding, good quality/size ratio)',
        'yify': 'YIFY (Same as YTS, efficient encoding)',
        'rarbg': 'RARBG (Balanced quality and size)',
        'ettv': 'ETTV (TV releases)',
        'eztv': 'EZTV (TV releases)',
        'sparks': 'SPARKS (High quality releases)',
        'deflate': 'DEFLATE (High quality)',
        'ntg': 'NTG (No Time to Gaming)',
        'qxr': 'QxR (High quality x265)',
        'tigole': 'Tigole (Efficient x265)',
        'successfulcrab': 'SuccessfulCrab',
        'rmteam': 'RMTeam',
        'pahe': 'PSA/PAHE (Efficient encoding)',
    }
    
    for group, description in group_info.items():
        if group in filename_lower:
            return description
    
    # Check for common patterns
    if 'web-dl' in filename_lower:
        return 'WEB-DL (High quality web source)'
    elif 'webrip' in filename_lower:
        return 'WEBRip (Web source)'
    elif 'bdrip' in filename_lower or 'bluray' in filename_lower:
        return 'BluRay source'
    elif 'dvdrip' in filename_lower:
        return 'DVD source'
    
    return 'Unknown group'

def detect_content_type(filename):
    """Enhanced content type detection"""
    filename_lower = filename.lower()
    
    # TV show patterns
    tv_patterns = [
        r's\d+e\d+',
        r'season\s*\d+.*episode\s*\d+',
        r'\d+x\d+',
        r'episode\s*\d+',
        r'ep\s*\d+',
    ]
    
    for pattern in tv_patterns:
        if re.search(pattern, filename_lower):
            return 'TV Episode'
    
    # Movie indicators
    movie_patterns = [
        r'\b(19[2-9]\d|20[0-4]\d)\b',  # Year
        r'\b(bluray|bdrip|dvdrip|webrip|web-dl)\b',
        r'\b(director|extended|uncut|ultimate|special|edition)\b',
    ]
    
    for pattern in movie_patterns:
        if re.search(pattern, filename_lower):
            return 'Movie'
    
    # Documentary indicators
    if any(term in filename_lower for term in ['documentary', 'docu', 'national.geographic', 'bbc', 'discovery']):
        return 'Documentary'
    
    return 'Unknown'

def get_confidence_label(score):
    """Convert confidence score to label"""
    if score >= 0.8:
        return "Very High"
    elif score >= 0.6:
        return "High"
    elif score >= 0.4:
        return "Medium"
    elif score >= 0.2:
        return "Low"
    else:
        return "Very Low"

def print_progress(message):
    """Print progress messages to stderr so they don't interfere with JSON output"""
    print(f"[INFO] {message}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description='Enhanced Torrent Bitrate Analyzer - Returns JSON by default',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "magnet:?xt=urn:btih:..."
  %(prog)s "magnet:?xt=urn:btih:..." -d 95
  %(prog)s "magnet:?xt=urn:btih:..." --quiet
  %(prog)s "magnet:?xt=urn:btih:..." --pretty
        """
    )
    parser.add_argument('magnet_url', help='Magnet URL to analyze')
    parser.add_argument('-d', '--duration', type=int, 
                       help='Manual duration in minutes (overrides estimation)')
    parser.add_argument('--pretty', action='store_true',
                       help='Pretty print JSON output with indentation')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress progress messages')
    
    args = parser.parse_args()
    
    try:
        # Set up progress callback
        progress_callback = None if args.quiet else print_progress
        
        # Analyze torrent
        result = get_torrent_info_from_magnet(
            args.magnet_url, 
            args.duration, 
            progress_callback
        )
        
        # Output JSON
        if args.pretty:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result))
                
    except KeyboardInterrupt:
        error_result = {
            'status': 'error',
            'error': 'Analysis interrupted by user',
            'error_type': 'user_interrupt'
        }
        print(json.dumps(error_result))
        return 1
    except Exception as e:
        error_result = {
            'status': 'error',
            'error': str(e),
            'error_type': 'analysis_error'
        }
        print(json.dumps(error_result))
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())