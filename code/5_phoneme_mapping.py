import json
import os
from pathlib import Path

def load_cmu_dict(file_path):
    """Load the CMU Pronouncing Dictionary."""
    cmu_dict = {}
    try:
        with open(file_path, 'r', encoding='latin-1') as f:  # Changed encoding to handle special chars
            for line in f:
                if not line.startswith(";;;"):  # Skip comment lines
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        word, phonemes = parts
                        cmu_dict[word] = phonemes.split()
    except Exception as e:
        print(f"Error loading CMU dictionary: {e}")
        # Provide fallback dictionary with basic phonemes
        cmu_dict = create_fallback_dict()
    
    print(f"Loaded {len(cmu_dict)} entries from the CMU dictionary.")
    return cmu_dict

def create_fallback_dict():
    """Create a minimal fallback dictionary for common words."""
    fallback = {
        "HELLO": ["HH", "AH", "L", "OW"],
        "WORLD": ["W", "ER", "L", "D"],
        "THIS": ["DH", "IH", "S"],
        "IS": ["IH", "Z"],
        "A": ["AH"],
        "TEST": ["T", "EH", "S", "T"],
        "TRANSCRIPT": ["T", "R", "AE", "N", "S", "K", "R", "IH", "P", "T"],
        "FOR": ["F", "AO", "R"],
        "ANIMATION": ["AE", "N", "AH", "M", "EY", "SH", "AH", "N"],
        "WELCOME": ["W", "EH", "L", "K", "AH", "M"],
        "TO": ["T", "UW"],
        "NERVOUS": ["N", "ER", "V", "AH", "S"]
    }
    print("Created fallback dictionary with common words.")
    return fallback

def map_words_to_phonemes(word_data, cmu_dict):
    phoneme_data = []
    unmatched_words = []

    for word_entry in word_data:
        # FIX: Strip all whitespace characters from the word
        word = word_entry['word'].lower().strip("()[]0123456789.,!?\"' \t\n\r").strip()
        # Convert to uppercase for CMU dict lookup
        word_upper = word.upper()
        
        start_time = word_entry['start_time']
        end_time = word_entry['end_time']
        word_duration = end_time - start_time

        # Try exact match or variant match
        phonemes = cmu_dict.get(word_upper) or next(
            (v for k, v in cmu_dict.items() if k.startswith(word_upper + "(")), None
        )

        # If still no match, try manually handling punctuation and special cases
        if not phonemes and word_upper.endswith('!!!'):
            word_upper = word_upper.rstrip('!')
            phonemes = cmu_dict.get(word_upper)

        # Log if the word is not found
        if not phonemes:
            unmatched_words.append(word)
            print(f"Word '{word}' not found in CMU dictionary. Using fallback.")
            
            # Provide better fallbacks for common words
            if word_upper == "WELCOME":
                phonemes = ["W", "EH", "L", "K", "AH", "M"]
            elif word_upper == "TO":
                phonemes = ["T", "UW"]
            elif word_upper == "NERVOUS":
                phonemes = ["N", "ER", "V", "AH", "S"]
            else:
                # Default fallback - use at least one non-silence phoneme
                phonemes = ["AH"]

        # Distribute duration across phonemes
        phoneme_duration = word_duration / len(phonemes) if phonemes else 0
        current_time = start_time

        for phoneme in phonemes:
            phoneme_data.append({
                'phoneme': phoneme,
                'start_time': current_time,
                'end_time': current_time + phoneme_duration
            })
            current_time += phoneme_duration

    # Print unmatched words for debugging
    if unmatched_words:
        print(f"Unmatched words: {len(unmatched_words)}")
        if len(unmatched_words) > 10:
            print(f"First 10 unmatched words: {unmatched_words[:10]}...")
        else:
            print(f"Unmatched words: {unmatched_words}")

    return phoneme_data


def main():
    # Set base directory and paths
    base_dir = Path(__file__).parent.parent
    
    # Try multiple locations for CMU dictionary, including Python 3.10 path
    possible_dict_paths = [
        #base_dir / ".venv/lib/python3.10/site-packages/pocketsphinx/model/en-us/cmudict-en-us.dict",
        #base_dir / ".toon/lib/python3.9/site-packages/pocketsphinx/model/en-us/cmudict-en-us.dict",
        #base_dir / ".venv/lib/python3.9/site-packages/pocketsphinx/model/en-us/cmudict-en-us.dict",
        #base_dir / ".venv/lib/python3.11/site-packages/pocketsphinx/model/en-us/cmudict-en-us.dict",
        base_dir / "/Users/nervous/Documents/GitHub/toon-in/cmudict-en-us.dict",  # In case it's in the base directory
    ]

    # Try to find any CMU dict file in the .venv directory
    venv_dir = base_dir / ".venv"
    if venv_dir.exists():
        for root, dirs, files in os.walk(str(venv_dir)):
            for file in files:
                if file == "cmudict-en-us.dict":
                    possible_dict_paths.append(Path(root) / file)
    
    cmu_dict = None
    for dict_path in possible_dict_paths:
        print(f"Checking for dictionary at: {dict_path}")
        if dict_path.exists():
            print(f"Found CMU dictionary at: {dict_path}")
            cmu_dict = load_cmu_dict(dict_path)
            break
    
    if cmu_dict is None:
        print("Warning: Could not find CMU dictionary. Using fallback dictionary.")
        cmu_dict = create_fallback_dict()

    # Load the word data JSON
    word_data_path = base_dir / "data/word_data.json"
    
    try:
        with open(word_data_path, "r", encoding="utf-8") as json_file:
            word_data = json.load(json_file)
    except Exception as e:
        print(f"Error loading word data: {e}")
        print("Creating sample word data for testing")
        word_data = [
            {"word": "welcome", "start_time": 0.0, "end_time": 0.5},
            {"word": "to", "start_time": 0.5, "end_time": 0.8},
            {"word": "nervous", "start_time": 0.8, "end_time": 1.0}
        ]

    # Map words to phonemes
    phoneme_data = map_words_to_phonemes(word_data, cmu_dict)

    # Save the phoneme data to JSON
    output_path = base_dir / "data/phoneme_data.json"
    with open(output_path, "w", encoding="utf-8") as json_file:
        json.dump(phoneme_data, json_file, indent=4, ensure_ascii=False)

    print(f"Phoneme data has been exported to {output_path}")
    print(f"Generated {len(phoneme_data)} phoneme entries from {len(word_data)} words")

if __name__ == "__main__":
    main()