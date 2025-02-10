import os
import multiprocessing as mp
from pathlib import Path
from tqdm import tqdm
from pydub import AudioSegment
from concurrent.futures import ProcessPoolExecutor, as_completed

def convert_to_wav(input_file):
    """Convert an audio file to WAV format with optimized settings."""
    try:
        output_file = str(Path(input_file).with_suffix('.wav'))
        
        # Load audio in chunks for memory efficiency
        audio = AudioSegment.from_file(input_file, format='mp3')
        
        # Process in a memory-efficient way by converting parameters directly
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        
        # Add silence more efficiently
        silence = AudioSegment.silent(duration=1000)
        audio = silence + audio + silence
        
        # Export with optimized settings
        audio.export(
            output_file,
            format="wav",
            parameters=[
                "-ar", "16000",  # Sample rate
                "-ac", "1",      # Channels
                "-acodec", "pcm_s16le"  # Codec
            ]
        )
        return True, input_file
    except Exception as e:
        return False, f"Error processing {input_file}: {str(e)}"

def process_directory(input_dir, max_workers=None):
    """Process all audio files in a directory using parallel processing."""
    input_dir = Path(input_dir)
    audio_files = list(input_dir.glob("*.mp3"))
    
    if not audio_files:
        print("No MP3 files found in the input directory.")
        return
    
    # Use number of CPU cores if max_workers not specified
    if max_workers is None:
        max_workers = mp.cpu_count()
    
    print(f"Processing {len(audio_files)} files using {max_workers} workers...")
    
    # Process files in parallel with progress bar
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_file = {
            executor.submit(convert_to_wav, str(file)): file
            for file in audio_files
        }
        
        # Track progress with tqdm
        with tqdm(total=len(audio_files), desc="Converting files") as pbar:
            for future in as_completed(future_to_file):
                success, result = future.result()
                if success:
                    pbar.write(f"Processed: {result}")
                else:
                    pbar.write(f"Failed: {result}")
                pbar.update(1)

def main():
    # Input and output directories
    input_dir = "/Users/nervous/Documents/GitHub/toon-in/data/audio/"
    
    # Create output directory if it doesn't exist
    os.makedirs(input_dir, exist_ok=True)
    
    # Optional: Set number of worker processes (default is number of CPU cores)
    max_workers = mp.cpu_count()  # You can adjust this number
    
    # Process files
    process_directory(input_dir, max_workers)

if __name__ == "__main__":
    main()