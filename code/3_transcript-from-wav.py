import whisper
import argparse
from pathlib import Path

def transcribe_and_save(audio_file, model_name="base", transcript_file="transcript.txt"):
    """
    Transcribe an audio file using Whisper and save the transcription as a text file.

    :param audio_file: Path to the audio file to transcribe.
    :param model_name: Whisper model to use (e.g., "base", "small", "medium", "large").
    :param transcript_file: Path to save the transcription as a text file.
    """
    # Load Whisper model
    model = whisper.load_model(model_name)

    # Transcribe audio
    print("Transcribing audio...")
    result = model.transcribe(audio_file)

    # Extract transcription text
    transcription = result.get("text", "").strip()

    # Save transcription to a text file
    try:
        with open(transcript_file, "w") as f:
            f.write(transcription)
        print(f"Transcription saved to {transcript_file}")
    except Exception as e:
        print(f"Error saving transcription:{e}")

def main():
    parser = argparse.ArgumentParser(description='Transcribe audio using Whisper')
    parser.add_argument('--audio_file', required=False, 
                        default=None,
                        help='Path to the audio file to transcribe')
    parser.add_argument('--model', required=False, default='base',
                        help='Whisper model to use (e.g., "base", "small", "medium", "large")')
    parser.add_argument('--output', required=False, 
                        default=None,
                        help='Path to save the transcription as a text file')
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    
    # Set default paths based on base directory if not provided
    if args.audio_file is None:
        args.audio_file = str(base_dir / "data/audio/dylan/dylan.wav")
    
    if args.output is None:
        args.output = str(base_dir / "data/clean_transcript.txt")
    
    transcribe_and_save(args.audio_file, args.model, args.output)