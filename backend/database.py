import mysql.connector

def get_connection():
    connection = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "Nayan@04",
        database = "banking_fraud_analytics"
    )

    return connection