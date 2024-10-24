import pandas as pd
import os
from datetime import datetime

# Create csvdata directory if it doesn't exist
if not os.path.exists('./csvdata'):
    os.makedirs('./csvdata')

# Get all xlsx files from xlsdata directory
xlsx_files = [f for f in os.listdir('./xlsdata') if f.endswith('.xlsx')]

# Sort files by date in filename
def extract_date(filename):
    date_str = filename.split('.')[0]  # Remove extension
    return datetime.strptime(date_str, '%Y-%m-%d_%H_%M_%S')

xlsx_files.sort(key=extract_date)

# Initialize empty DataFrame for combined data
combined_df = pd.DataFrame()

# Process each xlsx file and append to combined_df
for xlsx_file in xlsx_files:
    # Read xlsx file without headers
    df = pd.read_excel(f'./xlsdata/{xlsx_file}', header=None)
    
    # Filter rows containing "Интеллектуальн"
    df = df[df.apply(lambda row: any(str(cell).find('Интеллектуальн') != -1 for cell in row), axis=1)]
    
    # Remove rows containing the incorrect pattern
    df = df[~df.apply(lambda row: any(str(cell).find('Тип события:ANPR Автомобильный номер: Канал:') != -1 for cell in row), axis=1)]
    
    # Drop columns 1, 3, and 4 (using index 0-based)
    df = df.drop(df.columns[[0, 2, 3]], axis=1)
    
    # Clean text
    df = df.replace('Тип события:ANPR Автомобильный номер:', '', regex=True)
    
    # Skip header row by dropping first row
    df = df.iloc[1:]
    
    # Append to combined DataFrame
    combined_df = pd.concat([combined_df, df], ignore_index=True)
    
    print(f'Processed {xlsx_file}')

if not xlsx_files:
    print("No xlsx files found")
else:
    # Get date range for filename
    start_date = extract_date(xlsx_files[0]).strftime('%Y-%m-%d')
    end_date = extract_date(xlsx_files[-1]).strftime('%Y-%m-%d')
    
    # Create output filename with date range
    output_filename = f'combined_{start_date}_to_{end_date}.csv'
    
    # Save combined data to csv
    combined_df.to_csv(f'./csvdata/{output_filename}', index=False, header=False)
    print(f'Created combined file: {output_filename}')