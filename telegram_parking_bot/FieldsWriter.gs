/**
 * Создает ежедневный триггер для запуска в 07:05
 */
function createDailyTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'onChange') {
      ScriptApp.deleteTrigger(trigger);
    }
  });
  
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
  SpreadsheetApp.getUi()
      .createMenu('Действия')
      .addItem('Обновить данные', 'onChange')
      .addToUi();
}

/**
 * Обрабатывает изменения и обновляет данные между таблицами
 */
function onChange(e) {
  try {
    const spreadsheetIds = {
      source: '1uDNsA4GpRXWP5xQNUCr0s7l0ZyyJ7hThnQ6VSF1OwTI',
      target: '1oyaxJgF5tiLkholgWkUhdY_BIPFaP1cmKh-RJ2qMNGg',
      reference: '1jViFNLCbTRXBkvBdkUenq7K727gJNRp-IxRqBRIwJrI'
    };

    const spreadsheets = {
      source: SpreadsheetApp.openById(spreadsheetIds.source),
      target: SpreadsheetApp.openById(spreadsheetIds.target),
      reference: SpreadsheetApp.openById(spreadsheetIds.reference)
    };

    if (!Object.values(spreadsheets).every(sheet => sheet)) {
      throw new Error('Ошибка открытия таблиц');
    }

    const targetSheets = {
      coefficients: spreadsheets.target.getSheetByName('Коэффициенты'),
      cost: spreadsheets.target.getSheetByName('Стоимость')
    };

    if (!Object.values(targetSheets).every(sheet => sheet)) {
      throw new Error('Листы не найдены');
    }

    const coefficientsData = targetSheets.coefficients.getRange(1, 1, targetSheets.coefficients.getLastRow(), 2).getValues();
    const costData = targetSheets.cost.getRange(2, 1, targetSheets.cost.getLastRow() - 1, 4).getDisplayValues();

    const referenceSheet = spreadsheets.reference.getSheets()[0];
    if (!referenceSheet) throw new Error('Справочный лист не найден');
    const referenceData = referenceSheet.getRange(1, 1, referenceSheet.getLastRow(), 2).getValues();

    spreadsheets.source.getSheets().forEach(sourceSheet => {
      const sheetName = sourceSheet.getName();
      if (!/^\d{2}\.\d{4}$/.test(sheetName)) return;

      let targetSheet = getOrCreateTargetSheet(spreadsheets.target, sheetName);
      const lastRowSource = sourceSheet.getLastRow();
      if (lastRowSource < 2) return;

      const sourceData = sourceSheet.getRange(2, 1, lastRowSource - 1, 4).getValues();
      const currentCost = costData.find(row => row[0] === sheetName);
      
      if (!currentCost) return;

      const dayRate = parseFloat(currentCost[1].toString().replace(',', '.'));
      const minuteRate = parseFloat(currentCost[2].toString().replace(',', '.'));
      const hourlyRate = parseFloat(currentCost[3].toString().replace(',', '.'));

      const processedData = processSourceData(sourceData, referenceData, coefficientsData, dayRate, minuteRate, hourlyRate);
      
      if (processedData.length > 0) {
        if (targetSheet.getLastRow() > 1) {
          targetSheet.getRange(2, 1, targetSheet.getLastRow() - 1, 7).clearContent();
        }
        targetSheet.getRange(2, 1, processedData.length, 7).setValues(processedData);
      }
    });

    if (!e?.triggerUid) {
      SpreadsheetApp.getUi().alert('Данные успешно обновлены!');
    }
    
  } catch (error) {
    Logger.log('Ошибка: ' + error.toString());
    if (!e?.triggerUid) {
      SpreadsheetApp.getUi().alert('Произошла ошибка: ' + error.toString());
    }
  }
}

/**
 * Создает или получает целевой лист
 */
function getOrCreateTargetSheet(targetSpreadsheet, sheetName) {
  let targetSheet = targetSpreadsheet.getSheetByName(sheetName);
  if (!targetSheet) {
    targetSheet = targetSpreadsheet.insertSheet(sheetName);
    const headers = [['№', 'Номер', 'Тип', 'Период', 'Время на парковке', 'Коэффициент', 'Стоимость стоянки']];
    targetSheet.getRange(1, 1, 1, 7).setValues(headers);
  }
  return targetSheet;
}

/**
 * Конвертирует строку времени в минуты
 */
function timeStringToMinutes(timeStr) {
  if (!timeStr) return 0;
  
  let totalMinutes = 0;
  
  const daysMatch = timeStr.match(/(\d+)\s*д/);
  if (daysMatch) {
    totalMinutes += parseInt(daysMatch[1]) * 24 * 60;
  }
  
  const hoursMatch = timeStr.match(/(\d+)\s*ч/);
  if (hoursMatch) {
    totalMinutes += parseInt(hoursMatch[1]) * 60;
  }
  
  const minutesMatch = timeStr.match(/(\d+)\s*мин/);
  if (minutesMatch) {
    totalMinutes += parseInt(minutesMatch[1]);
  }
  
  return totalMinutes;
}

/**
 * Форматирует время для отображения
 */
function formatTime(minutes) {
  if (minutes < 24 * 60) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours} ч. ${remainingMinutes} мин.`;
  } else {
    const days = Math.floor(minutes / (24 * 60));
    const remainingHours = Math.floor((minutes % (24 * 60)) / 60);
    if (remainingHours > 0) {
      return `${days} д. ${remainingHours} ч.`;
    }
    return `${days} д.`;
  }
}

/**
 * Обрабатывает исходные данные и возвращает подготовленные данные для целевого листа
 */
function processSourceData(sourceData, referenceData, coefficientsData, dayRate, minuteRate, hourlyRate) {
  return sourceData.map((row, index) => {
    const carNumber = row[0];
    const referenceValue = referenceData.find(ref => ref[0] === carNumber);
    const timeInMinutes = timeStringToMinutes(row[3]);
    const formattedTime = formatTime(timeInMinutes);
    
    const coefficient = coefficientsData.find(coef => 
      referenceValue?.[1] && coef[0] && 
      referenceValue[1].toString().includes(coef[0].toString())
    );
    const coefficientValue = coefficient ? parseFloat(coefficient[1].toString().replace(',', '.')) : 0;
    
    let parkingCost;
    if (timeInMinutes >= 24 * 60) {
      // Для времени от 24 часов берем только целые дни (округление в меньшую сторону)
      const days = Math.floor(timeInMinutes / (24 * 60));
      parkingCost = days * dayRate * coefficientValue;
    } else if (timeInMinutes > 120) {
      // От 2 до 24 часов - считаем все время по почасовой ставке
      parkingCost = Math.ceil(timeInMinutes / 60) * hourlyRate * coefficientValue;
    } else {
      // До 2 часов - минутная ставка
      parkingCost = timeInMinutes * minuteRate * coefficientValue;
    }

    return [
      index + 1,
      carNumber,
      referenceValue ? referenceValue[1] : '',
      row[2] ? row[2].toString().replace(/, /g, '\n') : '',
      formattedTime,
      coefficientValue,
      parkingCost.toFixed(2) + ' BYN'
    ];
  });
}