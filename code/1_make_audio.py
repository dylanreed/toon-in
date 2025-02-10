import pandas as pd
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def text_to_speech(text, output_file):
    """
    Convert text to speech using Eleven Labs API with credentials from environment variables.
    
    Args:
        text (str): The text to convert to speech
        output_file (str): Path where the audio file will be saved
    """
    # Get credentials from environment variables
    api_key = os.getenv('ELEVENLABS_API_KEY')
    voice_id = os.getenv('ELEVENLABS_VOICE_ID')
    
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
        
        with open(output_file, "wb") as f:
            f.write(response.content)
        print(f"Audio saved to {output_file}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error generating audio: {str(e)}")
        if response.status_code == 401:
            print("Authentication failed. Please check your API key.")
        elif response.status_code == 404:
            print("Voice ID not found. Please check your voice ID.")
        else:
            print(f"Server response: {response.text}")

def main():
    # Path configurations
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, "input", "transcript.csv")
    output_dir = os.path.join(base_dir, "data", "audio")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Get the text from the CSV
        lines = df['text'].tolist()
        
        # Generate audio for each line
        for idx, line in enumerate(lines):
            output_file = os.path.join(output_dir, f"audio.mp3")
            print(f"Generating audio for line {idx + 1}: {line}")
            text_to_speech(line, output_file)
            
    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {csv_file}")
    except pd.errors.EmptyDataError:
        print("Error: The CSV file is empty")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()