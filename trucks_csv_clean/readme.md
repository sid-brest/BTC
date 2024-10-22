### Script cleans the 'Гос. номер' field, processes the data, removes duplicates, and creates a new CSV file with unique entries. 

Here's a breakdown of the main components:
1. The clean_gos_nomer function removes all non-alphanumeric characters from the input string.
2. The process_and_remove_duplicates function is the main workhorse of the script:
3. It opens the input CSV file and reads its contents.
4. It processes each row, cleaning the 'Гос. номер' field and filling in 'Нет данных' for empty fields.
5. It checks for duplicates based on the cleaned 'Гос. номер' field.
6. It keeps track of unique rows and duplicate information.
7. After processing all rows, it prints information about found duplicates.
8. Finally, it creates a new CSV file with only the unique rows.

The script uses command-line arguments to get the input file name, making it easy to use from the command line.
Error handling is implemented to catch and report file not found errors and other exceptions.