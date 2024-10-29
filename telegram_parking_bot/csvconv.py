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

# Функция для расчета временных интервалов
def calculate_time_intervals(df):
    results = []
    # Группируем по номерному знаку
    for plate, group in df.groupby('Номерной знак'):
        # Сортируем по времени
        group = group.sort_values('Время мом. снимка')
        
        # Преобразуем в список словарей для удобной обработки
        events = group.to_dict('records')
        
        i = 0
        intervals = []
        
        while i < len(events) - 1:
            if events[i]['Канал'] == 'CH01' and events[i + 1]['Канал'] == 'CH02':
                time_diff = (events[i + 1]['Время мом. снимка'] - events[i]['Время мом. снимка']).total_seconds() / 60
                intervals.append({
                    'start_time': events[i]['Время мом. снимка'].strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': events[i + 1]['Время мом. снимка'].strftime('%Y-%m-%d %H:%M:%S'),
                    'interval': round(time_diff, 2)
                })
            i += 1
        
        if intervals:
            total_minutes = sum(interval['interval'] for interval in intervals)
            # Конвертируем минуты в дни (1 день = 1440 минут)
            total_days = round(total_minutes / 1440, 3)
            results.append({
                'Номерной знак': plate,
                'Количество проездов': len(intervals),
                'Суммарное время (дни)': total_days,
                'Детали проездов': ', '.join([
                    f"({interval['start_time']} -> {interval['end_time']}: {interval['interval']} мин)"
                    for interval in intervals
                ])
            })
    
    return pd.DataFrame(results)

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

# Обрабатываем и сохраняем файлы по месяцам
for month_key, df in monthly_dfs.items():
    # Преобразуем столбец "Время мом. снимка" в datetime для корректной сортировки
    df['Время мом. снимка'] = pd.to_datetime(df['Время мом. снимка'])
    
    # Сортируем сначала по номерному знаку, затем по времени
    df_sorted = df.sort_values(['Номерной знак', 'Время мом. снимка'])
    
    # Сохраняем основной файл
    output_filename = f'./csvbymonth/data_{month_key}.csv'
    df_temp = df_sorted.copy()
    df_temp['Время мом. снимка'] = df_temp['Время мом. снимка'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_temp.to_csv(output_filename, index=False, encoding='utf-8-sig')
    
    # Рассчитываем и сохраняем временные интервалы
    intervals_df = calculate_time_intervals(df_sorted)
    intervals_filename = f'./csvbymonth/intervals_{month_key}.csv'
    intervals_df.to_csv(intervals_filename, index=False, encoding='utf-8-sig')

print("Обработка завершена. Проверьте папку csvbymonth для результатов.")