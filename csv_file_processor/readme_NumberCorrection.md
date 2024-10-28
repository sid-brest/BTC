# Google Sheets Auto-Formatting Script
## Overview
This Google Apps Script automatically formats text entered in column A of a Google Spreadsheet, converting Cyrillic characters to their Latin equivalents and standardizing the format.
## Features
- Converts Cyrillic letters to Latin equivalents
- Converts all text to uppercase
- Removes special characters and spaces
- Only processes column A (excluding header row)
- Maintains numbers in the text
## Installation
1. Open your Google Spreadsheet
2. Go to Tools > Script editor
3. Copy and paste the provided code
4. Save the project
5. Refresh your spreadsheet
## Usage
The script runs automatically when:
- You edit any cell in column A
- The edited cell is not in the first row (preserves headers)
### Example Transformations:
- "Привет-123" → "PBET123"
## Testing
Use the `testOnEdit()` function to test the functionality:
1. Open Script editor
2. Select `testOnEdit` function from the dropdown
3. Click Run
## Supported Characters
The following Cyrillic characters are converted:
- А → A
- В → B
- Е → E
- К → K
- М → M
- Н → H
- О → O
- Р → P
- С → C
- Т → T
- У → Y
- Х → X
## Notes
- The script only processes non-empty cells
- Changes are applied immediately upon edit
- Both uppercase and lowercase Cyrillic letters are supported