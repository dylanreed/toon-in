import pandas as pd
import requests
import os
import argparse
from dotenv import load_dotenv
from pathlib import Path

def text_to_speech(text, output_file, api_key, voice_id):
    """
    Convert text to speech using Eleven Labs API with credentials from environment variables.
    
    Args:
        text (str): The text to convert to speech
        output_file (str): Path where the audio file will be saved
        api_key (str): ElevenLabs API key
        voice_id (str): ElevenLabs voice ID
    """
    if not api_key or not voice_id:
        raise ValueError("Missing required environment variables. Please check your .env file.")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.75
        }
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Audio saved to {output_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error generating audio: {str(e)}")
        if hasattr(response, 'status_code'):
            if response.status_code == 401:
                print("Authentication failed. Please check your API key.")
            elif response.status_code == 404:
                print("Voice ID not found. Please check your voice ID.")
            else:
                print(f"Server response: {response.text}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate audio from text using ElevenLabs')
    parser.add_argument('--character', required=False, default='steve', choices=['steve', 'dylan'],
                        help='Character voice to use (steve or dylan)')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    api_key = os.getenv('ELEVENLABS_API_KEY')
    voice_id = os.getenv(f'ELEVENLABS_VOICE_ID_{args.character.upper()}', os.getenv('ELEVENLABS_VOICE_ID'))
    
    # Path configurations
    base_dir = Path(__file__).parent.parent
    csv_file = base_dir / "input" / "transcript.csv"
    output_file = base_dir / "data" / "audio" / args.character / f"episode_4_{args.character}.mp3"
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Get the text from the CSV
        lines = df['text'].tolist()
        
        # Generate audio for the combined text
        full_text = " ".join(lines)
        print(f"Generating audio for character {args.character}")
        text_to_speech(full_text, output_file, api_key, voice_id)
            
    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {csv_file}")
    except pd.errors.EmptyDataError:
        print("Error: The CSV file is empty")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()