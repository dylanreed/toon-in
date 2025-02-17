import csv

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

# Example Usage
save_csv_rows_as_txt('/Users/nervous/Documents/GitHub/toon-in/input/transcript.csv', '/Users/nervous/Documents/GitHub/toon-in/data/transcript.txt')