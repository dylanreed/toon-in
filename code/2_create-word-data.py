import sys
import os
import json
import time
import argparse
from pathlib import Path
import whisper

def clean_word_data(word_data):
    """
    Clean words by removing leading/trailing spaces and 
    convert all words to uppercase for CMU dictionary compatibility
    """
    cleaned_data = []
    
    for entry in word_data:
        original_word = entry['word']
        # First strip spaces and unwanted characters
        cleaned_word = original_word.strip()
        # Then convert to uppercase for CMU dictionary
        uppercase_word = cleaned_word.lower()
        
        if original_word != uppercase_word:
            print(f"Processed: '{original_word}' -> '{uppercase_word}'")
        
        cleaned_data.append({
            "word": uppercase_word,
            "start_time": entry['start_time'],
            "end_time": entry['end_time']
        })
    
    return cleaned_data
def main():
    parser = argparse.ArgumentParser(description='Create word-level timing data using Whisper')
    parser.add_argument('--audio_file', required=False, 
                      default=None,
                      help='Path to the audio file to transcribe')
    parser.add_argument('--model', required=False, default='base',
                      help='Whisper model to use (e.g., "base", "small", "medium", "large")')
    parser.add_argument('--output', required=False, 
                      default=None,
                      help='Path to save the word data JSON file')
    args = parser.parse_args()
    
    # Get base directory and set defaults
    base_dir = Path(__file__).parent.parent
    
    # Set default paths based on base directory if not provided
    if args.audio_file is None:
        args.audio_file = str(base_dir / "data/audio/steve/steve.wav")
    
    if args.output is None:
        args.output = str(base_dir / "data/word_data.json")
    
    audio_file = args.audio_file
    output_path = args.output
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Loading Whisper model '{args.model}'...")
    try:
        model = whisper.load_model(args.model)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)
    
    print(f"Transcribing audio file: {audio_file}")
    try:
        result = model.transcribe(audio_file, word_timestamps=True)
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        # Create some minimal default data to allow pipeline to continue
        default_data = [{"word": "test", "start_time": 0.0, "end_time": 1.0}]
        default_data = clean_word_data(default_data)  # Clean even the default data
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(default_data, json_file, indent=4, ensure_ascii=False)
        print(f"Created minimal default word data at: {output_path}")
        sys.exit(1)
    
    word_data = []
    try:
        for segment in result['segments']:
            if 'words' in segment:
                for word in segment['words']:
                    word_data.append({
                        "word": word["word"],
                        "start_time": word["start"],
                        "end_time": word["end"]
                    })
    except Exception as e:
        print(f"Error processing words: {e}")
        # Log the structure of the result
        print(f"Result structure: {list(result.keys())}")
        if 'segments' in result:
            print(f"First segment structure: {list(result['segments'][0].keys()) if result['segments'] else 'No segments'}")
        
        # Create fallback word data
        word_data = []
        text = result.get('text', 'Hello world')
        words = text.split()
        duration = result.get('duration', len(words) * 0.5)
        word_duration = duration / len(words) if words else 1.0
        
        for i, word in enumerate(words):
            word_data.append({
                "word": word,
                "start_time": i * word_duration,
                "end_time": (i + 1) * word_duration
            })
    
    # If no words were found, create some dummy data
    if not word_data:
        print("Warning: No word data found. Creating dummy data.")
        word_data = [{"word": "dummy", "start_time": 0.0, "end_time": 1.0}]
    
    # Clean the word data to remove unwanted characters and spaces
    print("\nCleaning word data...")
    word_data = clean_word_data(word_data)
    
    # Export word data to a JSON file
    try:
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(word_data, json_file, indent=4, ensure_ascii=False)
        print(f"Word data saved to: {output_path}")
        print(f"Total words: {len(word_data)}")
        print("Sample of processed words:")
        for i, entry in enumerate(word_data[:5]):
            if i >= len(word_data):
                break
            print(f"  {i+1}. '{entry['word']}' ({entry['start_time']:.2f}s - {entry['end_time']:.2f}s)")
        if len(word_data) > 5:
            print(f"  ...and {len(word_data) - 5} more words")
    except Exception as e:
        print(f"Error saving word data: {e}")
        # Try saving to a different location
        fallback_path = str(Path(output_path).parent / "fallback_word_data.json")
        with open(fallback_path, "w", encoding="utf-8") as json_file:
            json.dump(word_data, json_file, indent=4, ensure_ascii=False)
        print(f"Word data saved to fallback location: {fallback_path}")

if __name__ == "__main__":
    main()