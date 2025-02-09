import os
import random
from pydub import AudioSegment


def convert_to_wav(input_file, output_file):
    """Convert an audio file to WAV format with modifications."""
    try:
        audio = AudioSegment.from_file(input_file)

        # Apply the analog tape effect
        #audio = add_analog_tape_effect(audio)

        # Add 1 second of silence to the beginning and end
        silence = AudioSegment.silent(duration = 1000)  # 1 second of silence
        audio = silence + audio + silence

        # Convert audio to desired properties
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)

        # Export the audio to WAV format
        audio.export(output_file, format="wav")
        print(f"Converted and saved: {output_file}")
    except Exception as e:
        print(f"Error during conversion of {input_file}: {e}")

def main():
    # Input and output directories
    input_dir = "/Users/nervous/Documents/GitHub/toon-in/data/audio/"
    output_dir = "/Users/nervous/Documents/GitHub/toon-in/data/audio/"
    os.makedirs(output_dir, exist_ok=True)

    # Iterate over all audio files in the input directory
    for audio_file in os.listdir(input_dir):
        if audio_file.endswith(".mp3"):  # Process only .mp3 files
            input_file = os.path.join(input_dir, audio_file)
            output_file = os.path.join(output_dir, os.path.splitext(audio_file)[0] + ".wav")
            print(f"Processing {audio_file}...")
            convert_to_wav(input_file, output_file)

if __name__ == "__main__":
    main()
