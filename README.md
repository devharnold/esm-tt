# esm-tt
A timetable system built as a final year project.

1. Open the SQLite Database
Run the following command in your terminal to open the database:

sqlite3 projo.db

2. List All Tables
To see all the tables in your database:

.tables

3. View the Schema of a Table
To see the structure (columns and their types) of a specific table:

.schema table_name

Example:

.schema users

4. View All Data in a Table
To see all the rows in a specific table:

SELECT * FROM table_name;

Example:

SELECT * FROM users;

5. Count Rows in a Table
To count the number of rows in a table:

SELECT COUNT(*) FROM table_name;

Example:

SELECT COUNT(*) FROM timetables;

6. Filter Data in a Table
To filter data based on specific conditions:

SELECT * FROM table_name WHERE column_name = 'value';

Example:

SELECT * FROM timetable_requests WHERE status = 'pending';

7. List Column Names of a Table
To see the column names of a table:

PRAGMA table_info(table_name);

Example:

PRAGMA table_info(users);

8. Exit the SQLite Command-Line
To exit the SQLite terminal:

.exit

Example Workflow
Open the database:
List all tables:
View the schema of the timetables table:
View all data in the users table:
Exit SQLite:
These commands will help you explore and inspect your database directly from the SQLite command-line terminal.