import requests
import os
from tqdm import tqdm
import ffmpeg
from urllib.parse import urlparse, parse_qs

def clear_ts_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.ts'):
            file_path = os.path.join(directory, filename)
            os.remove(file_path)

def parse_shopee_url(url):
    """Parse Shopee Philippines live replay URL to extract session and record parameters"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Extract session from query parameters
        session = query_params.get('session', [None])[0]
        record = query_params.get('record', [None])[0]
        room_id = query_params.get('room_id', [None])[0]
        
        return {
            'session': session,
            'record': record,
            'room_id': room_id
        }
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None

def get_record_ids(session_id):
    replay_api_url = f'https://live.shopee.ph/api/v1/replay?session_id={session_id}'
    try:
        response = requests.get(replay_api_url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get('err_code') != 0:
            print(f"API Error: {data.get('err_msg', 'Unknown error')} for session ID: {session_id}")
            return None

        record_ids = data.get('data', {}).get('record_ids', [])
        return record_ids
    except requests.exceptions.RequestException as e:
        print(f"Network error while fetching record IDs: {e}")
        return None
    except ValueError as e:
        print(f"JSON decode error: {e}")
        return None

def get_m3u8_url(record_id):
    replay_api_url = f'https://live.shopee.ph/api/v1/replay/{record_id}'
    try:
        response = requests.get(replay_api_url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if data.get('err_code') != 0:
            print(f"API Error: {data.get('err_msg', 'Unknown error')} for record ID: {record_id}")
            return None

        replay_info = data.get('data', {}).get('replay_info', {})
        return replay_info.get('record_url', '')
    except requests.exceptions.RequestException as e:
        print(f"Network error while fetching M3U8 URL: {e}")
        return None
    except ValueError as e:
        print(f"JSON decode error: {e}")
        return None

def download_m3u8(record_id, output_dir='downloads', output_file='output.mp4'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    clear_ts_files(output_dir)

    m3u8_url = get_m3u8_url(record_id)
    if not m3u8_url:
        print(f"Failed to get M3U8 URL for record ID: {record_id}")
        return False

    try:
        m3u8_response = requests.get(m3u8_url, timeout=30)
        m3u8_response.raise_for_status()
        m3u8_content = m3u8_response.text
    except requests.exceptions.RequestException as e:
        print(f"Failed to download M3U8 content: {e}")
        return False

    lines = m3u8_content.split('\n')
    media_lines = [line.strip() for line in lines if line.strip().endswith('.ts')]
    
    if not media_lines:
        print("No video segments found in M3U8 file")
        return False

    user_input_output_file = input("Enter the output file name (including extension, e.g., output.mp4): ")
    output_file = user_input_output_file if user_input_output_file else f'shopee_replay_{record_id}.mp4'

    print(f"Found {len(media_lines)} segments to download")

    with tqdm(total=len(media_lines), desc='Downloading segments') as pbar:
        for index, media_line in enumerate(media_lines):
            try:
                if media_line.startswith('http'):
                    media_url = media_line
                else:
                    media_url = m3u8_url.rsplit('/', 1)[0] + '/' + media_line
                
                segment_file = os.path.join(output_dir, f'segment_{index}.ts')
                
                segment_response = requests.get(media_url, timeout=30)
                segment_response.raise_for_status()
                
                with open(segment_file, 'wb') as f:
                    f.write(segment_response.content)
                pbar.update(1)
            except requests.exceptions.RequestException as e:
                print(f"Failed to download segment {index}: {e}")
                continue

    concat_file_path = os.path.join(output_dir, 'concat.txt')
    with open(concat_file_path, 'w') as f:
        for index in range(len(media_lines)):
            segment_file = os.path.join(output_dir, f'segment_{index}.ts')
            if os.path.exists(segment_file):
                f.write(f"file 'segment_{index}.ts'\n")

    output_path = os.path.join(output_dir, output_file)
    
    try:
        (
            ffmpeg.input(concat_file_path, format='concat', safe=0)
            .output(output_path, c='copy')
            .run(overwrite_output=True, quiet=True)
        )
    except ffmpeg.Error as e:
        print(f"FFmpeg error during conversion: {e}")
        return False

    # Clean up temporary files
    for index in range(len(media_lines)):
        ts_file = os.path.join(output_dir, f'segment_{index}.ts')
        if os.path.exists(ts_file):
            os.remove(ts_file)
    
    # Clean up concat file
    if os.path.exists(concat_file_path):
        os.remove(concat_file_path)

    print(f'Conversion complete. Output saved to: {output_path}')
    return True

# Main execution
print("Shopee Philippines Live Replay Downloader")
print("=" * 40)

user_input = input("Enter Shopee live replay URL or session ID: ").strip()

# Check if input is a URL or session ID
if user_input.startswith('https://live.shopee.ph'):
    # Parse URL to extract parameters
    parsed_data = parse_shopee_url(user_input)
    if parsed_data and parsed_data['session']:
        session_id = parsed_data['session']
        record_id = parsed_data['record']
        print(f"Extracted session ID: {session_id}")
        if record_id:
            print(f"Extracted record ID: {record_id}")
    else:
        print("Failed to parse URL. Please check the URL format.")
        exit(1)
else:
    # Assume it's a session ID
    session_id = user_input
    record_id = None

# If we have a specific record ID from URL, use it directly
if record_id:
    print(f"Downloading specific record ID: {record_id}")
    success = download_m3u8(record_id)
    if not success:
        print("Download failed!")
        exit(1)
else:
    # Get all record IDs for the session
    record_ids = get_record_ids(session_id)
    
    if record_ids:
        print(f"Found {len(record_ids)} record(s) for session {session_id}")
        successful_downloads = 0
        for i, record_id in enumerate(record_ids, 1):
            print(f"Downloading record {i}/{len(record_ids)}: {record_id}")
            success = download_m3u8(record_id)
            if success:
                successful_downloads += 1
            print("-" * 40)
        
        print(f"Successfully downloaded {successful_downloads}/{len(record_ids)} records")
    else:
        print(f"No records found for session ID: {session_id}")
        print("Please check if the session ID is correct or if the replay is available.")
