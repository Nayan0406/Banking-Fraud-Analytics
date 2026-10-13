from database import get_connection

connection = get_connection()

if connection.is_connected():
    print("MySQL Database Connected Successfully!")

connection.close()