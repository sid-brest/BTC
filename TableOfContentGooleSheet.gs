function createTableOfContents() {
    const ss = SpreadsheetApp.getActive();
    const ssUrl = ss.getUrl();
    
    // Get all sheets and sort them by name
    let sheets = ss.getSheets();
    sheets.sort((a, b) => a.getName().localeCompare(b.getName(), undefined, {numeric: true, sensitivity: 'base'}));
    
    // Create array of [sheetUrl, sheetName] for all sheets except "Оглавление"
    const sheetArray = sheets
      .filter(sheet => sheet.getName() !== "Оглавление")
      .map(sheet => [`${ssUrl}#gid=${sheet.getSheetId()}`, sheet.getName()]);
    
    // Create rich text values with hyperlinks
    const richTextValues = sheetArray.map(f => [
      SpreadsheetApp.newRichTextValue()
        .setText(f[1])
        .setLinkUrl(f[0])
        .build()
    ]);
    
    // Get or create the TOC sheet
    const tocSheet = ss.getSheetByName('Оглавление') || ss.insertSheet('Оглавление', 0);
    
    // Clear existing content and set the new values
    tocSheet.clearContents();
    tocSheet.getRange(1, 1, richTextValues.length, 1).setRichTextValues(richTextValues);
    
    // Auto-resize the column
    tocSheet.autoResizeColumn(1);
    
    // Move TOC sheet to the first position
    ss.setActiveSheet(tocSheet);
    ss.moveActiveSheet(1);
    
    // Sort other sheets
    sortSheets();
  }
  
  function sortSheets() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sheets = ss.getSheets();
    
    // Sort sheets by name, keeping "Оглавление" at the beginning
    sheets.sort((a, b) => {
      if (a.getName() === "Оглавление") return -1;
      if (b.getName() === "Оглавление") return 1;
      return a.getName().localeCompare(b.getName(), undefined, {numeric: true, sensitivity: 'base'});
    });
    
    // Reorder sheets
    sheets.forEach((sheet, index) => {
      ss.setActiveSheet(sheet);
      ss.moveActiveSheet(index + 1);
    });
  }
  
  function onOpen() {
    const ui = SpreadsheetApp.getUi();
    ui.createMenu('Custom Menu')
      .addItem('Create Table of Contents', 'createTableOfContents')
      .addToUi();
  }