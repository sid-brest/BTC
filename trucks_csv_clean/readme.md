# CSV File Processor
## Description
This Python script processes CSV files by performing the following operations:
1. Converts Russian characters to their Latin lookalikes
2. Removes duplicates based on the first column
3. Reformats datetime values from DD-MM-YY HH:MM to YYYY-MM-DD HH:MM
4. Cleans text data by removing special characters and content in parentheses
## Features
- Duplicate detection and removal (keeping the last occurrence)
- Russian to Latin character conversion
- DateTime format standardization
- Special character removal
- Detailed processing report with statistics
## Requirements
- Python 3.x
- Required Python packages:
  - pandas
  - csv (built-in)
  - re (built-in)
  - os (built-in)
  - datetime (built-in)
## Installation
1. Ensure Python 3.x is installed on your system
2. Install required packages:
```bash
pip install pandas
```
## Usage
1. Place your CSV file in the same directory as the script
2. Run the script:
```bash
python script_name.py
```
3. Enter the name of your input CSV file when prompted
4. The processed file will be saved with "_modified" added to the original filename
## Input File Requirements
1. CSV file format
2. UTF-8 encoding
3. If contains dates, they should be in DD-MM-YY HH:MM format
## Output
1. Creates a new CSV file with "_modified" suffix
2. Uses UTF-8-BOM encoding
3. All fields are quoted
4. Includes comma and newline as terminators
## Example
Input filename: data.csv
Output filename: data_modified.csv
## Character Conversion Table
Russian characters are converted to their Latin lookalikes as follows:
```bash
А → A    а → a
В → B    в → b
Е → E    е → e
К → K    к → k
М → M    м → m
Н → H    н → h
О → O    о → o
Р → P    р → p
С → C    с → c
Т → T    т → t
У → Y    у → y
Х → X    х → x
```
## Processing Steps
1. Reads input CSV file with UTF-8-BOM encoding
2. Identifies and reports duplicates in the first column
3. Removes duplicates (keeps last occurrence)
4. Formats datetime columns if present
5.  Processes text in the first column:
6. Removes content in parentheses
7. Removes special characters
8. Converts Russian characters to Latin
9. Saves processed data to new CSV file
## Error Handling
1. Handles NaN (empty) values
2. Safely processes datetime conversions
3. Maintains original data if datetime conversion fails
## Notes
1. Original file remains unchanged
2. Processing report shows number of duplicates removed
3. All changes are saved to a new file with "_modified" suffix