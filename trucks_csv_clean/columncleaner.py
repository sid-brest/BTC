import csv
import re
import os

def process_value(value):
    # Удаляем информацию в скобках вместе со скобками
    value = re.sub(r'\([^)]*\)', '', value)
    # Удаляем все символы, кроме букв, цифр и подчеркиваний
    value = re.sub(r'[^\w]', '', value)
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