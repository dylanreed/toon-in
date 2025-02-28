import re
import json
import os
import sys
from pathlib import Path

def load_file(file_path):
    """Load text or JSON file content."""
    if file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif file_path.endswith(".json"):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file format for file: {file_path}")

def parse_transcript_with_emotions(transcript, words_timing):
    """
    Parse transcript for emotions in parentheses and generate timing data.

    Args:
        transcript (str): The transcript text with emotion tags (e.g., "(smile)").
        words_timing (list): List of dictionaries with word timings.

    Returns:
        list: Emotion data with start and end times.
    """
    emotion_pattern = re.compile(r"\((.*?)\)")
    emotion_data = []
    valid_emotions = ["neutral", "cringe", "frown", "mockery", "sad", "smile_2", "smile"]

    for match in re.finditer(emotion_pattern, transcript):
        emotion = match.group(1)  # Extract emotion name
        if emotion not in valid_emotions:
            print(f"Warning: Emotion '{emotion}' not in valid emotions list. Skipping...")
            continue

        # Calculate position in transcript
        position = match.start() / len(transcript) * words_timing[-1]["end_time"]

        # Find closest word timing
        closest_word = min(words_timing, key=lambda x: abs(x["start_time"] - position))

        emotion_data.append({
            "pose_folder": "emotions",
            "pose_image": f"emotions/{emotion}.png",
            "pose_start_time": closest_word["start_time"],
            "pose_end_time": closest_word["end_time"] + 1.0  # Extend duration for emotions
        })

    return emotion_data

def save_emotion_data(emotion_data, output_file):
    """Save the emotion data to a JSON file."""
    # Load existing pose data if it exists
    existing_data = []
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not read existing data from {output_file}")

    # Combine existing pose data with new emotion data
    combined_data = existing_data + emotion_data

    # Sort by start_time
    combined_data.sort(key=lambda x: x["pose_start_time"])

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=4)
    print(f"Emotion data saved to: {output_file}")

if __name__ == "__main__":
    # Get base directory
    base_dir = Path(__file__).parent.parent
    
    # File paths
    transcript_file = base_dir / "data/transcript.txt"
    words_timing_file = base_dir / "data/word_data.json"
    output_file = base_dir / "data/emotion_data.json"

    # Verify files exist
    if not transcript_file.exists():
        print(f"Error: Transcript file not found at {transcript_file}")
        sys.exit(1)
        
    if not words_timing_file.exists():
        print(f"Error: Word timing file not found at {words_timing_file}")
        sys.exit(1)

    # Load input files
    try:
        transcript = load_file(str(transcript_file))
        words_timing = load_file(str(words_timing_file))
    except Exception as e:
        print(f"Error loading input files: {e}")
        sys.exit(1)

    # Parse emotions from the transcript
    try:
        emotion_data = parse_transcript_with_emotions(transcript, words_timing)
        # Save the emotion data (will be combined with existing pose data)
        save_emotion_data(emotion_data, str(output_file))
    except Exception as e:
        print(f"Error processing emotion data: {e}")
        sys.exit(1)