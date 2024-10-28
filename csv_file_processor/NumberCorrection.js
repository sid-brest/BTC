/**
 * Trigger function that runs when a cell is edited in the spreadsheet
 * @param {Object} e - Event object containing information about the edit
 */
function onEdit(e) {
  // Exit if no event object is provided (manual function execution)
  if (!e) return;
  
  var sheet = e.source.getActiveSheet();
  var range = e.range;
  
  // Only process edits in the first column (A) and not in the header row
  if (range.getColumn() == 1 && range.getRow() > 1) {
    var value = e.value;
    // Exit if cell was cleared
    if (!value) return;
    
    // Dictionary for replacing Cyrillic letters with Latin equivalents
    // Includes both uppercase and lowercase Cyrillic letters
    var replacements = {
      'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
      'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
      'а': 'A', 'в': 'B', 'е': 'E', 'к': 'K', 'м': 'M', 'н': 'H',
      'о': 'O', 'р': 'P', 'с': 'C', 'т': 'T', 'у': 'Y', 'х': 'X'
    };
    
    // Convert the string to array, replace each character, then join back
    var newValue = value.split('').map(function(char) {
      // If character exists in replacements, use it; otherwise convert to uppercase
      return replacements[char] || char.toUpperCase();
    }).join('');
    
    // Remove all special characters and spaces, keep only A-Z and 0-9
    newValue = newValue.replace(/[^A-Z0-9]/g, '');
    
    // Update cell only if the value has changed
    if (newValue !== value) {
      range.setValue(newValue);
    }
  }
}

/**
 * Test function to simulate onEdit trigger
 * Can be run manually to test the functionality
 */
function testOnEdit() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var range = sheet.getRange(2, 1); // Second row, first column
  
  // Create mock event object
  var testEvent = {
    source: SpreadsheetApp.getActive(),
    range: range,
    value: "АВС 123"
  };
  
  onEdit(testEvent);
}