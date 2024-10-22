import csv
import re
import sys
import os
from collections import defaultdict

def clean_gos_nomer(value):
    # Remove all characters except letters and numbers
    return re.sub(r'[^a-zA-Z0-9]', '', value)

def process_and_remove_duplicates(input_file):
    duplicates = defaultdict(list)
    line_numbers = {}
    unique_rows = []
    
    try:
        # Open the input file
        with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Define the fieldnames for the output file
            fieldnames = ['Гос. номер', 'Марка тех.пасп.', 'Собственник']
            
            # Add headers to unique_rows
            unique_rows.append(fieldnames)
            
            print(f"Checking for duplicates in the first column: '{fieldnames[0]}'")
            
            # Process each row in the input file
            for i, row in enumerate(reader, start=2):  # start=2 because row 1 is headers
                # Clean and process the 'Гос. номер' field
                gos_nomer = clean_gos_nomer(row['Гос. номер'])
                
                if gos_nomer:  # Check if the number is not empty after cleaning
                    # Create a new row with cleaned and processed data
                    new_row = [
                        gos_nomer,
                        row['Марка тех.пасп.'] or 'Нет данных',
                        row['Собственник'] or 'Нет данных'
                    ]
                    
                    # Check for duplicates
                    if gos_nomer not in duplicates:
                        unique_rows.append(new_row)
                    
                    # Record duplicate information
                    duplicates[gos_nomer].append(i)
                    line_numbers[i] = new_row
        
        # Print information about found duplicates
        print("\nFound duplicates:")
        found_duplicates = False
        for value, lines in duplicates.items():
            if len(lines) > 1:
                found_duplicates = True
                print(f"\nValue '{value}' found in the following lines:")
                for line in lines:
                    print(f"  Line {line}: {line_numbers[line]}")
        
        if not found_duplicates:
            print("No duplicates found.")

        # Create a new file without duplicates
        output_file = f"output_{os.path.basename(input_file)}"
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(unique_rows)
        
        print(f"\nCreated a new file without duplicates: {output_file}")

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Check if the correct number of command-line arguments is provided
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <input_file.csv>")
        sys.exit(1)
    
    # Get the input file name from command-line arguments
    input_file = sys.argv[1]
    
    # Process the file and remove duplicates
    process_and_remove_duplicates(input_file)