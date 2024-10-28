import pandas as pd
import csv
import re
import os
from datetime import datetime

def russian_to_latin(text):
    rus_to_lat = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
        'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
        'а': 'a', 'в': 'b', 'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h',
        'о': 'o', 'р': 'p', 'с': 'c', 'т': 't', 'у': 'y', 'х': 'x'
    }
    return ''.join(rus_to_lat.get(char, char) for char in str(text))

def process_value(value):
    if pd.isna(value):
        return ''
    value = str(value)
    value = re.sub(r'\([^)]*\)', '', value)
    value = re.sub(r'[^\w]', '', value)
    value = russian_to_latin(value)
    return value

def format_datetime(df):
    for col in df.columns:
        # Check if column contains date-like values
        sample_value = df[col].iloc[0] if not df.empty else None
        if isinstance(sample_value, str) and re.search(r'\d{2}-\d{2}-\d{2}\s+\d{1,2}:\d{2}', str(sample_value)):
            try:
                # Convert from DD-MM-YY HH:MM to YYYY-MM-DD HH:MM
                df[col] = pd.to_datetime(df[col], format='%d-%m-%y %H:%M')
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M')
            except:
                continue
    return df

def process_csv(input_file):
    # Read CSV file
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    
    # Format datetime columns
    df = format_datetime(df)
    
    # Find duplicates in first column BEFORE processing
    first_col = df.columns[0]
    duplicates = df[df.duplicated(subset=first_col, keep=False)]
    
    if len(duplicates) > 0:
        print("\nFound duplicates:")
        for value in duplicates[first_col].unique():
            if pd.notna(value):  # Only print non-empty values
                print(f"'{value}' appears {len(duplicates[duplicates[first_col] == value])} times")
        print(f"\nTotal duplicates found: {len(duplicates)}")
    else:
        print("No duplicates found")
    
    # Drop duplicates based on first column (keep last occurrence)
    df_no_dupes = df.drop_duplicates(subset=first_col, keep='last')
    
    print(f"\nRows before: {len(df)}")
    print(f"Rows after: {len(df_no_dupes)}")
    print(f"Removed {len(df) - len(df_no_dupes)} duplicate rows")
    
    # Now process the first column in the deduplicated dataframe
    df_no_dupes[first_col] = df_no_dupes[first_col].apply(process_value)
    
    # Generate output filename
    base_name, ext = os.path.splitext(input_file)
    output_file = f"{base_name}_modified{ext}"
    
    # Save results to new CSV file
    df_no_dupes.to_csv(output_file, index=False, encoding='utf-8-sig', 
                       quoting=csv.QUOTE_ALL, lineterminator=',\n')
    
    print(f"\nProcessed file saved as: {output_file}")

# Usage
input_file = input("Enter input CSV filename: ")
process_csv(input_file)