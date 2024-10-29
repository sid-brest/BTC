import os
import pandas as pd
from datetime import datetime
import re

# Создаем папки если не существуют
os.makedirs('./csvdata', exist_ok=True)
os.makedirs('./csvbymonth', exist_ok=True)

# Функция для определения канала по IP адресу
def get_channel(filename):
    ip_match = re.search(r'192\.168\.4\.(\d+)', filename)
    if ip_match:
        ip_last_octet = ip_match.group(1)
        if ip_last_octet == '103':
            return 'CH01'
        elif ip_last_octet == '104':
            return 'CH02'
    return 'Unknown'

# Получаем список всех CSV файлов в папке csvdata
csv_files = [f for f in os.listdir('./csvdata') if f.endswith('.CSV')]

# Словарь для хранения DataFrame по месяцам
monthly_dfs = {}

# Обрабатываем каждый файл
for file in csv_files:
    # Извлекаем дату из имени файла
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file)
    if date_match:
        file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
        month_key = file_date.strftime('%Y-%m')
        
        # Читаем CSV файл
        df = pd.read_csv(f'./csvdata/{file}', encoding='utf-8')
        
        # Удаляем строки где "Номерной знак" содержит "Не лицензировано"
        df = df[df['Номерной знак'] != 'Не лицензировано']
        
        # Выбираем только нужные колонки
        selected_columns = ['Номерной знак', 'Белый список', 'Время мом. снимка', 'ТС спереди или сзади']
        df = df[selected_columns].copy()
        
        # Добавляем столбец Канал
        df.insert(0, 'Канал', get_channel(file))
        
        # Добавляем DataFrame в соответствующий месяц
        if month_key in monthly_dfs:
            monthly_dfs[month_key] = pd.concat([monthly_dfs[month_key], df], ignore_index=True)
        else:
            monthly_dfs[month_key] = df

# Сохраняем файлы по месяцам
for month_key, df in monthly_dfs.items():
    output_filename = f'./csvbymonth/data_{month_key}.csv'
    df.to_csv(output_filename, index=False, encoding='utf-8')