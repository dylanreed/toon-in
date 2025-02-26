#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import shutil
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd

# Base directory setup
BASE_DIR = Path(__file__).parent.parent

def print_header(step_num, description):
    """Print a formatted header for each step"""
    print("\n" + "=" * 80)
    print(f"STEP {step_num}: {description}")
    print("=" * 80)

def run_command(command, ignore_errors=False):
    """Run a shell command and handle errors"""
    try:
        print(f"Running: {command}")
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"STDERR: {e.stderr}")
        if not ignore_errors:
            print("Pipeline stopped due to error. Fix the issue and try again.")
            sys.exit(1)
        return False

def ensure_directories():
    """Create necessary directories if they don't exist"""
    dirs = [
        BASE_DIR / "data",
        BASE_DIR / "data" / "audio",
        BASE_DIR / "data" / "audio" / "steve",
        BASE_DIR / "data" / "audio" / "dylan",
        BASE_DIR / "output",
        BASE_DIR / "output" / "steve",
        BASE_DIR / "output" / "dylan",
        BASE_DIR / "input"
    ]
    
    for directory in dirs:
        directory.mkdir(exist_ok=True, parents=True)
        print(f"Ensured directory exists: {directory}")
        
    # Create a simple test transcript CSV if none exists
    transcript_csv = BASE_DIR / "input" / "transcript.csv"
    if not transcript_csv.exists():
        print(f"Creating sample transcript CSV at {transcript_csv}")
        with open(transcript_csv, 'w') as f:
            f.write("text\nHello, this is a test transcript for animation.")

def select_voice():
    """Let user select which character voice to use"""
    while True:
        choice = input("\nSelect character (1=Steve, 2=Dylan): ").strip()
        if choice == '1':
            return 'steve'
        elif choice == '2':
            return 'dylan'
        else:
            print("Invalid choice. Please enter 1 for Steve or 2 for Dylan.")

def get_voice_id(character):
    """Get the appropriate voice ID from .env file"""
    load_dotenv()
    
    # Look for character-specific voice ID first
    voice_id = os.getenv(f'ELEVENLABS_VOICE_ID_{character.upper()}')
    
    # Fall back to default voice ID if specific one not found
    if not voice_id:
        voice_id = os.getenv('ELEVENLABS_VOICE_ID')
        
    if not voice_id:
        print("Error: No voice ID found in .env file.")
        print("Please add ELEVENLABS_VOICE_ID or ELEVENLABS_VOICE_ID_STEVE/ELEVENLABS_VOICE_ID_DYLAN to your .env file.")
        sys.exit(1)
        
    return voice_id

def update_env(character, voice_id):
    """Update .env file with the selected voice ID"""
    env_path = BASE_DIR / ".env"
    
    # Create .env file if it doesn't exist
    if not env_path.exists():
        with open(env_path, 'w') as f:
            f.write(f"ELEVENLABS_VOICE_ID={voice_id}\n")
    else:
        # Read existing content
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        # Update or add the voice ID
        voice_id_updated = False
        for i, line in enumerate(lines):
            if line.startswith('ELEVENLABS_VOICE_ID='):
                lines[i] = f"ELEVENLABS_VOICE_ID={voice_id}\n"
                voice_id_updated = True
        
        if not voice_id_updated:
            lines.append(f"ELEVENLABS_VOICE_ID={voice_id}\n")
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(lines)
    
    print(f"Updated .env file with voice ID for {character}")

def run_animation_pipeline():
    """Run the entire animation pipeline"""
    start_time = time.time()
    
    # Ensure all required directories exist
    ensure_directories()
    
    # Get user selection for character
    character = select_voice()
    voice_id = get_voice_id(character)
    update_env(character, voice_id)
    
    # Set file paths based on character
    audio_path = f"data/audio/{character}/{character}.wav"
    output_video = f"output/{character}/{character}_episode_4_output.mp4"
    animation_script = f"code/9_{character}_norris.py" if character == "dylan" else "code/9_steve_norris.py"
    
    # Define absolute paths
    audio_mp3 = BASE_DIR / f"data/audio/{character}/{character}.mp3"
    audio_wav = BASE_DIR / f"data/audio/{character}/{character}.wav"
    transcript_txt = BASE_DIR / "data/transcript.txt"
    word_data_json = BASE_DIR / "data/word_data.json"
    
    # STEP 1: Generate audio from transcript
    print_header(1, "Generate audio from transcript")
    run_command(f"python {BASE_DIR}/code/0_make_audio.py --character {character}")
    
    # Verify MP3 was created
    if not audio_mp3.exists():
        print(f"Error: MP3 file not created at {audio_mp3}")
        print("Trying to create directory and retry...")
        audio_mp3.parent.mkdir(exist_ok=True, parents=True)
        run_command(f"python {BASE_DIR}/code/0_make_audio.py --character {character}")
        if not audio_mp3.exists():
            print(f"Fatal error: Failed to create MP3 file at {audio_mp3}")
            sys.exit(1)
    else:
        print(f"MP3 created successfully: {audio_mp3}")
    
    # STEP 2: Convert audio to WAV format
    print_header(2, "Convert audio to WAV format")
    run_command(f"python {BASE_DIR}/code/1_audio_conversion.py --audio_dir {audio_mp3.parent}")
    
    # Verify WAV was created
    if not audio_wav.exists():
        print(f"Error: WAV file not created at {audio_wav}")
        print("Creating WAV manually...")
        import subprocess
        subprocess.run(f"ffmpeg -i {audio_mp3} -ar 16000 -ac 1 {audio_wav}", shell=True, check=True)
        if not audio_wav.exists():
            print(f"Fatal error: Failed to create WAV file at {audio_wav}")
            sys.exit(1)
    else:
        print(f"WAV created successfully: {audio_wav}")
    
    # STEP 3: Generate transcript from audio
    print_header(3, "Generate transcript from audio")
    run_command(f"python {BASE_DIR}/code/3_transcript-from-wav.py --audio_file {audio_wav} --output {transcript_txt}")
    
    # STEP 4: Convert CSV to TXT if necessary
    print_header(4, "Convert CSV to TXT if needed")
    if (BASE_DIR / "input" / "transcript.csv").exists():
        run_command(f"python {BASE_DIR}/code/4_csv_to_txt.py --output_txt {transcript_txt}")
    else:
        print("No CSV file found, using transcript from audio")
    
    # STEP 5: Create word timing data
    print_header(5, "Create word timing data")
    run_command(f"python {BASE_DIR}/code/2_create-word-data.py --audio_file {audio_wav} --output {word_data_json}")
    
    # Verify word data was created
    if not word_data_json.exists():
        print(f"Error: Word data file not created at {word_data_json}")
        print("Trying to create directory and retry...")
        word_data_json.parent.mkdir(exist_ok=True, parents=True)
        run_command(f"python {BASE_DIR}/code/2_create-word-data.py --audio_file {audio_wav} --output {word_data_json}")
        if not word_data_json.exists():
            print(f"Fatal error: Failed to create word data file at {word_data_json}")
            sys.exit(1)
    else:
        print(f"Word data created successfully: {word_data_json}")
    
    # STEP 6: Map phonemes
    print_header(6, "Map phonemes")
    run_command(f"python {BASE_DIR}/code/5_phoneme_mapping.py")
    
    # STEP 7: Generate emotion data
    print_header(7, "Generate emotion data")
    run_command(f"python {BASE_DIR}/code/6_emotion_data.py")
    
    # STEP 8: Generate pose data
    print_header(8, "Generate pose data")
    run_command(f"python {BASE_DIR}/code/7_pose_data.py")
    
    # Verify all required files exist for animation
    if not audio_wav.exists():
        print(f"Error: Audio file not found at {audio_wav}")
        sys.exit(1)
    
    # Ensure output directory exists
    output_video_path = Path(output_video)
    output_video_path.parent.mkdir(exist_ok=True, parents=True)
    
    # STEP 9: Run animation
    print_header(9, "Run animation")
    animation_cmd = f"python {BASE_DIR}/{animation_script}"
    animation_cmd += f" --audio_path {audio_wav}"
    animation_cmd += f" --output_path {output_video}"
    animation_cmd += " --threaded"
    
    print(f"Running animation command: {animation_cmd}")
    run_command(animation_cmd)
    
    # Done!
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"ANIMATION PIPELINE COMPLETED in {elapsed_time:.2f} seconds!")
    print(f"Output video: {output_video}")
    print("=" * 80)

if __name__ == "__main__":
    try:
        run_animation_pipeline()
    except KeyboardInterrupt:
        print("\nAnimation pipeline interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError in animation pipeline: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)