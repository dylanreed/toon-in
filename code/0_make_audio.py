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
    parser.add_argument('--input_txt', required=False, default=None,
                        help='Path to input text file (defaults to input/transcript.txt)')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment variables
    api_key = os.getenv('ELEVENLABS_API_KEY')
    voice_id = os.getenv(f'ELEVENLABS_VOICE_ID_{args.character.upper()}', os.getenv('ELEVENLABS_VOICE_ID'))
    
    # Path configurations
    base_dir = Path(__file__).parent.parent
    
    # Input text file path
    input_txt = args.input_txt
    if input_txt is None:
        input_txt = base_dir / "input" / "transcript.txt"
        # Check if transcript.txt exists, if not look for transcript.csv content
        if not input_txt.exists():
            csv_file = base_dir / "input" / "transcript.csv"
            if csv_file.exists():
                # Create a simple transcript from CSV
                try:
                    with open(csv_file, 'r') as f:
                        lines = f.readlines()
                        # Skip header if it looks like a header
                        if lines and "text" in lines[0].lower():
                            lines = lines[1:]
                        with open(input_txt, 'w') as txt_out:
                            txt_out.writelines(lines)
                    print(f"Created text file from CSV: {input_txt}")
                except Exception as e:
                    print(f"Error converting CSV to text: {e}")
                    # Create a default text file
                    with open(input_txt, 'w') as f:
                        f.write("This is a default text for animation testing.")
                    print(f"Created default text file: {input_txt}")
            else:
                # Create a default text file
                with open(input_txt, 'w') as f:
                    f.write("This is a default text for animation testing.")
                print(f"Created default text file: {input_txt}")
    
    # Output file path
    output_file = base_dir / "data" / "audio" / args.character / f"{args.character}.mp3"
    
    try:
        # Read the text file
        if not os.path.exists(input_txt):
            raise FileNotFoundError(f"Text file not found: {input_txt}")
            
        with open(input_txt, 'r') as f:
            text = f.read().strip()
        
        if not text:
            raise ValueError("The text file is empty")
            
        # Generate audio for the text
        print(f"Generating audio for character {args.character}")
        print(f"Text content: {text[:100]}..." if len(text) > 100 else f"Text content: {text}")
        text_to_speech(text, output_file, api_key, voice_id)
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        # Create a simple default text if all else fails
        default_text = "This is a fallback test sentence for animation."
        print(f"Using default text: {default_text}")
        text_to_speech(default_text, output_file, api_key, voice_id)

if __name__ == "__main__":
    main()