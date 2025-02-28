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

def parse_transcript_with_poses(transcript, words_timing):
    """
    Parse transcript for poses and generate timing data for each pose.

    Args:
        transcript (str): The transcript text with pose tags (e.g., "<wave>").
        words_timing (list): List of dictionaries with word timings.

    Returns:
        list: Pose data with start and end times.
    """
    pose_pattern = re.compile(r"<(.*?)>")
    pose_data = []

    for match in re.finditer(pose_pattern, transcript):
        pose = match.group(1)  # Extract pose name
        position = match.start() / len(transcript) * words_timing[-1]["end_time"]

        closest_word = min(words_timing, key=lambda x: abs(x["start_time"] - position))

        # Dynamically determine pose folder
        if "att_2" in pose:  # Assign pose_2 to att_2
            pose_folder = "brows"
        else:
            pose_folder = "brows"

        pose_data.append({
            "pose_folder": pose_folder,
            "pose_image": f"{pose_folder}/{pose}.png",
            "pose_start_time": closest_word["start_time"],
            "pose_end_time": closest_word["end_time"] + 0.5  # Extend duration slightly
        })

    return pose_data

def save_pose_data(pose_data, output_file):
    """Save the pose data to a JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pose_data, f, indent=4)
    print(f"Pose data saved to: {output_file}")

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    
    # File paths
    transcript_file = base_dir / "input/transcript.txt"
    words_timing_file = base_dir / "data/word_data.json"
    output_file = base_dir / "data/pose_data.json"

    # Load input files
    transcript = load_file(str(transcript_file))
    words_timing = load_file(str(words_timing_file))

    # Parse poses/emotions from the transcript
    pose_data = parse_transcript_with_poses(transcript, words_timing)

    # Save the pose/emotion data
    save_pose_data(pose_data, str(output_file))
