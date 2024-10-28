import csv
import re
import os

def russian_to_latin(text):
    # Словарь для замены русских букв на латинские аналоги
    rus_to_lat = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H',
        'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
        'а': 'a', 'в': 'b', 'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h',
        'о': 'o', 'р': 'p', 'с': 'c', 'т': 't', 'у': 'y', 'х': 'x'
    }
    return ''.join(rus_to_lat.get(char, char) for char in text)

def process_value(value):
    # Удаляем информацию в скобках вместе со скобками
    value = re.sub(r'\([^)]*\)', '', value)
    # Удаляем все символы, кроме букв, цифр и подчеркиваний
    value = re.sub(r'[^\w]', '', value)
    # Заменяем русские буквы на латинские
    value = russian_to_latin(value)
    return value

def process_csv(input_file):
    base_name, ext = os.path.splitext(input_file)
    output_file = f"{base_name}_modified{ext}"
    
    with open(input_file, 'r', newline='', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        for row in reader:
            # Пропускаем пустые строки
            if not any(row):
                continue
            
            # Обрабатываем каждое значение в строке
            processed_row = [process_value(value) for value in row]
            
            # Записываем обработанную строку в новый файл
            writer.writerow(processed_row)
    
    print(f"Обработанный файл сохранен как: {output_file}")

# Использование функции
input_file = input("Введите имя входного CSV файла: ")
process_csv(input_file)