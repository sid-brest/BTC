import pandas as pd
from datetime import datetime
import os

# Create reports directory if it doesn't exist
if not os.path.exists('./reports'):
    os.makedirs('./reports')

# Read the CSV file
df = pd.read_csv('your_input.csv', header=None, names=['datetime', 'info'])

# Split the info column into car number and channel
df['car_number'] = df['info'].apply(lambda x: x.split()[0])
df['channel'] = df['info'].str.extract(r'Канал:(\d+)')
df['datetime'] = pd.to_datetime(df['datetime'])
df['date'] = df['datetime'].dt.date

# Function to calculate parking duration for a car on a specific date
def calculate_parking_time(group):
    entries = group[group['channel'] == '1'].sort_values('datetime')
    exits = group[group['channel'] == '2'].sort_values('datetime')
    
    total_duration = pd.Timedelta(0)
    
    for entry in entries['datetime']:
        # Find the next exit after this entry
        valid_exits = exits[exits['datetime'] > entry]
        if not valid_exits.empty:
            exit_time = valid_exits.iloc[0]['datetime']
            duration = exit_time - entry
            total_duration += duration
            # Remove used exit to avoid counting it again
            exits = exits[exits['datetime'] > exit_time]
    
    return total_duration.total_seconds() / 3600  # Convert to hours

# Group by car number and date, then calculate parking duration
results = []
for (date, car), group in df.groupby(['date', 'car_number']):
    hours = calculate_parking_time(group)
    results.append({
        'car_number': car,
        'date': date,
        'hours': round(hours, 2)
    })

# Create result DataFrame and sort by date and car number
result_df = pd.DataFrame(results)
result_df = result_df.sort_values(['date', 'car_number'])

# Save to CSV file with date range in filename
min_date = df['date'].min().strftime('%Y-%m-%d')
max_date = df['date'].max().strftime('%Y-%m-%d')
output_filename = f'./reports/parking_duration_{min_date}_to_{max_date}.csv'

# Save results
result_df.to_csv(output_filename, index=False)

print(f'Report has been saved to {output_filename}')