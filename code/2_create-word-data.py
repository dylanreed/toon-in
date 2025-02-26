# 2_create-word-data.py modification
import whisper
import json
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Create word-level timing data using Whisper')
    parser.add_argument('--audio_file', required=False, 
                      default='/Users/nervous/Documents/GitHub/toon-in/data/audio/dylan/dylan.wav',
                      help='Path to the audio file to transcribe')
    parser.add_argument('--model', required=False, default='medium',
                      help='Whisper model to use (e.g., "base", "small", "medium", "large")')
    parser.add_argument('--output', required=False, 
                      default='/Users/nervous/Documents/GitHub/toon-in/data/word_data.json',
                      help='Path to save the word data JSON file')
    args = parser.parse_args()
    
    base_dir = Path(args.audio_file).parent.parent.parent
    
    print(f"Loading Whisper model '{args.model}'...")
    model = whisper.load_model(args.model)
    
    print(f"Transcribing audio file: {args.audio_file}")
    result = model.transcribe(args.audio_file, word_timestamps=True)
    
    word_data = []
    for segment in result['segments']:
        for word in segment['words']:
            word_data.append({
                "word": word["word"],
                "start_time": word["start"],
                "end_time": word["end"]
            })
    
    # Export word data to a JSON file
    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(word_data, json_file, indent=4, ensure_ascii=False)
    
    print(f"Word data saved to: {output_path}")

if __name__ == "__main__":
    main()