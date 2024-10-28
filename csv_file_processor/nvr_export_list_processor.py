# Import required libraries
import pandas as pd  # For data manipulation and analysis
import csv          # For CSV file operations
import re           # For regular expression operations
import os           # For file path operations
from datetime import datetime  # For datetime operations

def russian_to_latin(text):
    """
    Convert Russian characters to their Latin lookalikes
    Args:
        text: Input string containing Russian characters
    Returns:
        String with Russian characters replaced by Latin equivalents
    """
    rus_to_lat = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
        'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
        'а': 'a', 'в': 'b', 'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h',
        'о': 'o', 'р': 'p', 'с': 'c', 'т': 't', 'у': 'y', 'х': 'x'
    }
    # Replace each character if it exists in mapping, otherwise keep original
    return ''.join(rus_to_lat.get(char, char) for char in str(text))

def process_value(value):
    """
    Process a single value: handle NaN, remove parentheses and special characters,
    and convert Russian characters to Latin
    Args:
        value: Input value to process
    Returns:
        Processed string value
    """
    if pd.isna(value):  # Check for NaN values
        return ''
    value = str(value)
    value = re.sub(r'\([^)]*\)', '', value)  # Remove content within parentheses
    value = re.sub(r'[^\w]', '', value)      # Remove non-word characters
    value = russian_to_latin(value)          # Convert Russian to Latin characters
    return value

def format_datetime(df):
    """
    Convert datetime strings in DataFrame from DD-MM-YY HH:MM to YYYY-MM-DD HH:MM
    Args:
        df: Input DataFrame
    Returns:
        DataFrame with formatted datetime columns
    """
    for col in df.columns:
        # Check if column contains date-like values
        sample_value = df[col].iloc[0] if not df.empty else None
        if isinstance(sample_value, str) and re.search(r'\d{2}-\d{2}-\d{2}\s+\d{1,2}:\d{2}', str(sample_value)):
            try:
                # Convert datetime format
                df[col] = pd.to_datetime(df[col], format='%d-%m-%y %H:%M')
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M')
            except:
                continue
    return df

def process_csv(input_file):
    """
    Main function to process CSV file: handle duplicates, format dates,
    and clean data
    Args:
        input_file: Path to input CSV file
    """
    # Read CSV file with UTF-8 BOM encoding
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    
    # Format datetime columns in the DataFrame
    df = format_datetime(df)
    
    # Check for duplicates in first column before processing
    first_col = df.columns[0]
    duplicates = df[df.duplicated(subset=first_col, keep=False)]
    
    # Print duplicate information if found
    if len(duplicates) > 0:
        print("\nFound duplicates:")
        for value in duplicates[first_col].unique():
            if pd.notna(value):  # Only print non-empty values
                print(f"'{value}' appears {len(duplicates[duplicates[first_col] == value])} times")
        print(f"\nTotal duplicates found: {len(duplicates)}")
    else:
        print("No duplicates found")
    
    # Remove duplicates, keeping only the last occurrence
    df_no_dupes = df.drop_duplicates(subset=first_col, keep='last')
    
    # Print summary of duplicate removal
    print(f"\nRows before: {len(df)}")
    print(f"Rows after: {len(df_no_dupes)}")
    print(f"Removed {len(df) - len(df_no_dupes)} duplicate rows")
    
    # Process the first column in the deduplicated DataFrame
    df_no_dupes[first_col] = df_no_dupes[first_col].apply(process_value)
    
    # Create output filename by adding '_modified' before extension
    base_name, ext = os.path.splitext(input_file)
    output_file = f"{base_name}_modified{ext}"
    
    # Save processed DataFrame to new CSV file
    # Use UTF-8 BOM encoding, quote all fields, and add comma+newline as terminator
    df_no_dupes.to_csv(output_file, index=False, encoding='utf-8-sig', 
                       quoting=csv.QUOTE_ALL, lineterminator=',\n')
    
    print(f"\nProcessed file saved as: {output_file}")

# Script execution
input_file = input("Enter input CSV filename: ")  # Get input filename from user
process_csv(input_file)  # Process the CSV file