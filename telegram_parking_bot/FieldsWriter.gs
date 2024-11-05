/**
 * Создает ежедневный триггер для запуска в 07:05
 */
function createDailyTrigger() {
  // Удаляем существующие триггеры с тем же именем функции
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'onChange') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
  // Создаем новый ежедневный триггер
  ScriptApp.newTrigger('onChange')
      .timeBased()
      .atHour(7)
      .nearMinute(5)
      .everyDays(1)
      .create();
}

/**
 * Создает пользовательское меню при открытии таблицы
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Действия')
      .addItem('Обновить данные', 'onChange')
      .addToUi();
}

/**
 * Обрабатывает изменения и обновляет данные между таблицами
 * @param {Object} e - Объект события
 */
function onChange(e) {
  try {
    // ID таблиц
    const sourceSpreadsheetId = '1uDNsA4GpRXWP5xQNUCr0s7l0ZyyJ7hThnQ6VSF1OwTI';    // Исходная таблица
    const targetSpreadsheetId = '1oyaxJgF5tiLkholgWkUhdY_BIPFaP1cmKh-RJ2qMNGg';    // Целевая таблица
    const referenceSpreadsheetId = '1jViFNLCbTRXBkvBdkUenq7K727gJNRp-IxRqBRIwJrI'; // Справочная таблица

    // Открытие таблиц
    const sourceSpreadsheet = SpreadsheetApp.openById(sourceSpreadsheetId);
    const targetSpreadsheet = SpreadsheetApp.openById(targetSpreadsheetId);
    const referenceSpreadsheet = SpreadsheetApp.openById(referenceSpreadsheetId);

    if (!sourceSpreadsheet || !targetSpreadsheet || !referenceSpreadsheet) {
      Logger.log('Ошибка открытия таблиц');
      return;
    }

    // Получение листов с коэффициентами и стоимостью
    const coefficientsSheet = targetSpreadsheet.getSheetByName('Коэффициенты');
    const costSheet = targetSpreadsheet.getSheetByName('Стоимость');
    
    if (!coefficientsSheet || !costSheet) {
      Logger.log('Листы не найдены');
      return;
    }

    // Загрузка данных коэффициентов и стоимости
    const coefficientsData = coefficientsSheet.getRange(1, 1, coefficientsSheet.getLastRow(), 2).getValues();
    const costData = costSheet.getRange(2, 1, costSheet.getLastRow() - 1, 2).getDisplayValues();

    const sourceSheets = sourceSpreadsheet.getSheets();

    // Обработка каждого листа исходной таблицы
    for (const sourceSheet of sourceSheets) {
      const sheetName = sourceSheet.getName();
      
      // Проверка формата имени листа (ММ.ГГГГ)
      if (!/^\d{2}\.\d{4}$/.test(sheetName)) continue;

      // Создание или получение целевого листа
      let targetSheet = targetSpreadsheet.getSheetByName(sheetName);
      if (!targetSheet) {
        const [month, year] = sheetName.split('.');
        const prevDate = new Date(parseInt(year), parseInt(month) - 2, 1);
        const prevSheetName = `${String(prevDate.getMonth() + 1).padStart(2, '0')}.${prevDate.getFullYear()}`;
        
        const prevSheet = targetSpreadsheet.getSheetByName(prevSheetName);
        
        if (prevSheet) {
          // Копирование структуры предыдущего листа
          targetSheet = prevSheet.copyTo(targetSpreadsheet).setName(sheetName);
          const range = targetSheet.getRange(2, 1, targetSheet.getLastRow() - 1, targetSheet.getLastColumn());
          range.clearContent();
        } else {
          // Создание нового листа с заголовками
          targetSheet = targetSpreadsheet.insertSheet(sheetName);
          targetSheet.getRange('A1:G1').setValues([['№', 'Номер', 'Тип', 'Период', 'Время на парковке', 'Коэффициент', 'Стоимость стоянки']]);
        }
      }

      // Получение справочных данных
      const referenceSheet = referenceSpreadsheet.getSheets()[0];
      if (!referenceSheet) continue;

      const lastRowSource = sourceSheet.getLastRow();
      const lastRowRef = referenceSheet.getLastRow();

      if (lastRowSource < 2 || lastRowRef < 2) continue;

      // Получение данных из исходного и справочного листов
      const sourceData = sourceSheet.getRange(2, 1, lastRowSource - 1, 3).getValues();
      const referenceData = referenceSheet.getRange(1, 1, lastRowRef, 2).getValues();
      
      // Поиск стоимости для текущего периода
      const hourlyCost = costData.find(row => row[0] === sheetName);
      const hourlyCostValue = hourlyCost ? parseFloat(hourlyCost[1].toString().replace(',', '.')) : 0;

      // Обработка и подготовка данных для целевого листа
      const targetData = sourceData.map((row, index) => {
        const targetRow = [];
        targetRow.push(index + 1); // №
        targetRow.push(row[0] || ''); // Номер
        
        const referenceValue = referenceData.find(ref => ref[0] === row[0]);
        targetRow.push(referenceValue ? referenceValue[1] : ''); // Тип
        
        targetRow.push(row[2] ? row[2].toString().replace(/, /g, '\n') : ''); // Период
        
        // Расчет количества дней и часов
        const timeStr = row[2] ? row[2].toString() : '';
        const daysMatch = timeStr.match(/(\d+)\s*д/);
        const hoursMatch = timeStr.match(/(\d+)\s*ч/);
        
        const days = daysMatch ? parseInt(daysMatch[1]) : 0;
        const hours = hoursMatch ? parseInt(hoursMatch[1]) : 0;
        
        const totalHours = (days * 24) + hours;
        targetRow.push(totalHours + ' ч.'); // Время на парковке в часах
        
        // Поиск и применение коэффициента
        const coefficient = coefficientsData.find(coef => 
          referenceValue && referenceValue[1] && 
          coef[0] && referenceValue[1].toString().includes(coef[0].toString())
        );
        const coefficientValue = coefficient ? parseFloat(coefficient[1].toString().replace(',', '.')) : 0;
        targetRow.push(coefficientValue); // Коэффициент
        
        // Расчет стоимости стоянки (теперь используем почасовую ставку)
        const parkingCost = totalHours * coefficientValue * hourlyCostValue;
        targetRow.push(parkingCost.toFixed(2) + ' BYN'); // Стоимость стоянки в формате BYN
        
        return targetRow;
      });

      // Запись данных в целевой лист
      if (targetData.length > 0) {
        targetSheet.getRange(2, 1, targetData.length, 7).setValues(targetData);
      }
    }

    // Показ уведомления при ручном запуске
    if (!e || !e.triggerUid) {
      SpreadsheetApp.getUi().alert('Данные успешно обновлены!');
    }
    
  } catch (error) {
    if (!e || !e.triggerUid) {
      SpreadsheetApp.getUi().alert('Произошла ошибка: ' + error.toString());
    }
    Logger.log('Ошибка: ' + error.toString());
  }
}