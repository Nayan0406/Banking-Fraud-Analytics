import pandas as pd
from database import get_connection

def load_transactions():

    connection = get_connection()

    query = """
    select * from transactions
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df