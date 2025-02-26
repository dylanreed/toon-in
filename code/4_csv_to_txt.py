import csv
import argparse
from pathlib import Path

def save_csv_rows_as_txt(input_csv, output_txt):
    """Reads a CSV file and saves each row as text in a .txt file."""
    text_rows = []
    
    with open(input_csv, 'r', encoding='utf-8') as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            text_rows.append(' '.join(row))  # Join row elements with a space
    
    with open(output_txt, 'w', encoding='utf-8') as txt_file:
        txt_file.write('\n'.join(text_rows))
    
    print(f"Text saved to {output_txt}")

def main():
    parser = argparse.ArgumentParser(description='Convert CSV to text file')
    parser.add_argument('--input_csv', required=False, 
                        default='/Users/nervous/Documents/GitHub/toon-in/input/transcript.csv',
                        help='Path to the input CSV file')
    parser.add_argument('--output_txt', required=False, 
                        default='/Users/nervous/Documents/GitHub/toon-in/data/transcript.txt',
                        help='Path to save the output text file')
    args = parser.parse_args()
    
    save_csv_rows_as_txt(args.input_csv, args.output_txt)

if __name__ == "__main__":
    main()