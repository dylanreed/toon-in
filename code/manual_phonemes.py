import json
from pathlib import Path

def create_manual_phoneme_data():
    """
    Create phoneme data directly using a predefined mapping rather than
    trying to use the CMU dictionary.
    """
    # Get base directory
    base_dir = Path(__file__).parent.parent
    word_data_path = base_dir / "data/word_data.json"
    
    # Manual mapping of words to phonemes for the transcript
    manual_word_phonemes = {
        "WELCOME": ["W", "EH", "L", "K", "AH", "M"],
        "TO": ["T", "UW"],
        "NERVOUS": ["N", "ER", "V", "AH", "S"],
        "HOWDY": ["HH", "AW", "D", "IY"],
        "THERE": ["DH", "EH", "R"],
        "FOLKS": ["F", "OW", "K", "S"],
        "DOES": ["D", "AH", "Z"],
        "DISCORD": ["D", "IH", "S", "K", "AO", "R", "D"],
        "MAKE": ["M", "EY", "K"],
        "YOU": ["Y", "UW"],
    }
    
    # Add basic defaults for any other word
    for word in ["THE", "THIS", "THAT", "AND", "IS", "ARE", "A", "AN", "IN", "OUT"]:
        if word not in manual_word_phonemes:
            manual_word_phonemes[word] = ["AH"]
    
    # Load word data
    try:
        with open(word_data_path, "r", encoding="utf-8") as f:
            word_data = json.load(f)
    except Exception as e:
        print(f"Error loading word data: {e}")
        # Create dummy word data
        word_data = [
            {"word": "WELCOME", "start_time": 0.0, "end_time": 0.5},
            {"word": "TO", "start_time": 0.5, "end_time": 0.8},
            {"word": "NERVOUS", "start_time": 0.8, "end_time": 1.2}
        ]
    
    # Create phoneme data
    phoneme_data = []
    for word_entry in word_data:
        word = word_entry.get("word", "").upper()  # Ensure uppercase
        start_time = word_entry.get("start_time", 0)
        end_time = word_entry.get("end_time", 0)
        duration = end_time - start_time
        
        # Get phonemes for this word
        phonemes = manual_word_phonemes.get(word, ["AH"])
        
        # Calculate duration for each phoneme
        phoneme_duration = duration / len(phonemes) if phonemes else 0
        current_time = start_time
        
        # Create a phoneme entry for each phoneme
        for phoneme in phonemes:
            phoneme_data.append({
                "phoneme": phoneme,
                "start_time": current_time,
                "end_time": current_time + phoneme_duration
            })
            current_time += phoneme_duration
            
    # Save phoneme data
    output_path = base_dir / "data/phoneme_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(phoneme_data, f, indent=4)
    
    print(f"Created {len(phoneme_data)} phoneme entries for {len(word_data)} words")
    
    # Show some examples of what we created
    for i, entry in enumerate(phoneme_data[:10]):
        if i >= len(phoneme_data):
            break
        print(f"  {i+1}. Phoneme: {entry['phoneme']}, Time: {entry['start_time']:.2f}-{entry['end_time']:.2f}")

if __name__ == "__main__":
    create_manual_phoneme_data()