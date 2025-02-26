import json
from pathlib import Path

def map_phonemes_to_visemes(phoneme_data):
    """
    Map phoneme data to viseme data using the updated phoneme-to-image mappings.
    """
    phoneme_to_mouth_shape = {
        # Vowels
        "AA": "aei.png",  # as in "odd"
        "AE": "aei.png",  # as in "at"
        "AH": "aei.png",  # as in "hut"
        "AO": "o.png",    # as in "ought"
        "EH": "ee.png",   # as in "ed"
        "IH": "ee.png",   # as in "it"
        "IY": "ee.png",   # as in "eat"
        "UH": "o.png",    # as in "hood"
        "UW": "o.png",    # as in "two"
        
        # Diphthongs
        "AY": "aei.png",  # as in "hide"
        "EY": "ee.png",   # as in "ate"
        "OW": "o.png",    # as in "oat"
        "OY": "o.png",    # as in "toy"
        
        # Consonants
        "B": "bmp.png",   # as in "be"
        "M": "bmp.png",   # as in "me"
        "P": "bmp.png",   # as in "pee"
        
        "C": "cdgknstxyz.png",  # as in "see"
        "D": "cdgknstxyz.png",  # as in "dee"
        "G": "cdgknstxyz.png",  # as in "green"
        "K": "cdgknstxyz.png",  # as in "key"
        "N": "cdgknstxyz.png",  # as in "knee"
        "S": "cdgknstxyz.png",  # as in "sea"
        "T": "cdgknstxyz.png",  # as in "tea"
        "X": "cdgknstxyz.png",  # as in "exit"
        "Y": "cdgknstxyz.png",  # as in "yield"
        "Z": "cdgknstxyz.png",  # as in "zee"
        
        "F": "fv.png",    # as in "fee"
        "V": "fv.png",    # as in "vee"
        
        "L": "l.png",     # as in "lee"
        "R": "r.png",     # as in "read"
        
        "W": "qw.png",    # as in "we"
        "Q": "qw.png",    # as in "queen"
        
        "SH": "shch.png", # as in "she"
        "CH": "shch.png", # as in "cheese"
        "JH": "shch.png", # as in "joy"
        
        "TH": "th.png",   # as in "thin"
        "DH": "th.png",   # as in "this"
        
        "SIL": "neutral.png"  # silence
    }

    viseme_list = []
    for entry in phoneme_data:
        phoneme = entry['phoneme']
        # Default to neutral.png instead of aei.png for unknown phonemes
        mouth_shape = phoneme_to_mouth_shape.get(phoneme, "neutral.png")

        viseme_list.append({
            "viseme": mouth_shape,
            "start_time": entry['start_time'],
            "end_time": entry['end_time']
        })

    return viseme_list


if __name__ == "__main__":
    # Use relative paths based on script location
    base_dir = Path(__file__).parent.parent
    
    # Load phoneme data from the JSON file
    phoneme_data_path = base_dir / "data/phoneme_data.json"
    with open(phoneme_data_path, "r", encoding="utf-8") as json_file:
        phoneme_data = json.load(json_file)

    # Map phonemes to visemes
    viseme_data = map_phonemes_to_visemes(phoneme_data)

    # Save viseme data to a new JSON file
    viseme_data_path = base_dir / "data/viseme_data.json"
    with open(viseme_data_path, "w", encoding="utf-8") as json_file:
        json.dump(viseme_data, json_file, indent=4)

    print(f"Viseme data has been exported to {viseme_data_path}")