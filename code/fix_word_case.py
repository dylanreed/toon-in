import json
from pathlib import Path

def fix_word_data_case():
    """
    Load word_data.json, convert all words to uppercase, and save it back.
    This is a simple fix to run before continuing the pipeline.
    """
    # Get base directory
    base_dir = Path(__file__).parent.parent
    word_data_path = base_dir / "data/word_data.json"
    
    try:
        # Load the current word data
        with open(word_data_path, "r", encoding="utf-8") as f:
            word_data = json.load(f)
        
        # Convert all words to uppercase
        for entry in word_data:
            if 'word' in entry:
                entry['word'] = entry['word'].upper()
        
        # Save the modified data back
        with open(word_data_path, "w", encoding="utf-8") as f:
            json.dump(word_data, f, indent=4)
        
        print(f"Successfully converted {len(word_data)} words to uppercase in {word_data_path}")
        
        # Print a few samples
        for i, entry in enumerate(word_data[:5]):
            if i >= len(word_data):
                break
            print(f"  {i+1}. '{entry['word']}'")
        
    except Exception as e:
        print(f"Error fixing word data case: {e}")

if __name__ == "__main__":
    fix_word_data_case()