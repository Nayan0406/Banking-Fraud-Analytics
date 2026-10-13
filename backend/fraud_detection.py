import pandas as pd
from database import get_connection

def load_transactions():

    connection = get_connection()

    query = """
    select
        transaction_id,
        account_id,
        amount,
        transaction_type,
        payment_method,
        transaction_date,
        location,
        status
    from transactions
    """

    df = pd.read_sql(query, connection)

    connection.close()

    return df

def detect_fraud(df):

    #Risk score initially 0
    df["risk_score"] = 0

    #fraud reasons
    df["fraud_reasons"] = ""

    #Rule 1: High transaction amount
    high_amount = df["amount"] > 100000

    df.loc[high_amount, "risk_score"] += 30
    df.loc[high_amount, "fraud_reasons"] += "High transaction amount; "

    #Rule 2: Late night transaction
    df["transaction_hour"] = pd.to_datetime(
        df["transaction_date"]
    ).dt.hour

    late_night = df["transaction_hour"].between(0, 5)

    df.loc[late_night, "risk_score"] += 20
    df.loc[late_night, "fraud_reasons"] += 'Unusual transaction time; '

    #Rule 3: Failed transaction
    failed_transaction = df["status"] == "Failed"

    df.loc[failed_transaction, "risk_score"] += 15
    df.loc[failed_transaction, "fraud_reasons"] += "Failed transaction; "

    #Rule 4: Rapid transactions
    df = df.sort_values(
        ["account_id", "transaction_date"]
    ).reset_index(drop=True)

    df["previous_transaction_time"] = (
        df.groupby("account_id")["transaction_date"].shift(1)
    )

    df["time_difference_minutes"] = (
        pd.to_datetime(df["transaction_date"]) -
        pd.to_datetime(df["previous_transaction_time"])
    ).dt.total_seconds() / 60

    rapid_transaction = (
        (df["time_difference_minutes"] <= 10) &
        (df["time_difference_minutes"] >= 0)
    )

    df.loc[rapid_transaction, "risk_score"] += 25

    df.loc[
        rapid_transaction,
        "fraud_reasons"
    ] += "Multiple transactions within 10 minutes;"

    #Rule 5: Locatio anomaly detection

    df["previous_location"] = (
        df.groupby("account_id")["location"].shift(1)
    )

    location_anomaly = (
        (df["time_difference_minutes"] >= 0)
        & (df["time_difference_minutes"] <= 30)
        & df["previous_location"].notna()
        & df["location"].notna()
        & (df["location"] != df["previous_location"])
    )

    df.loc[location_anomaly, "risk_score"] += 25

    df.loc[
        location_anomaly,
        "fraud_reasons"
    ] += "Location changed within 30 minutes;"

    #Risk level
    df["risk_level"] = "Low"

    df.loc[
        df["risk_score"].between(31, 60),
        "risk_level"
    ] = "Medium"

    df.loc[
        df["risk_score"] > 60,
        "risk_level"
    ] = "High"

    return df

def save_fraud_alerts(df):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        suspicious = df[df["risk_score"] > 0]

        for _, row in suspicious.iterrows():
            cursor.execute(
                """
                SELECT alert_id
                from fraud_alerts
                where transaction_id = %s
                """,
                (int(row["transaction_id"]),)
            )

            if cursor.fetchone():
                continue

            cursor.execute(
                """
                insert into fraud_alerts
                (transaction_id, risk_score, risk_level, fraud_reason)
                values (%s, %s, %s, %s)
                """,
                (
                    int(row["transaction_id"]),
                    float(row["risk_score"]),
                    row["risk_level"],
                    row["fraud_reasons"].strip()
                )
            )

        connection.commit()
        print("Fraud alerts saved successfully!")

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":

    transactions = load_transactions()

    print("Total transactions:", len(transactions))

    result = detect_fraud(transactions)

    suspicious = result[result["risk_score"] > 0]

    print("\nSuspicious Transactions:")
    print(
        suspicious[
            [
                "transaction_id",
                "account_id",
                "amount",
                "transaction_hour",
                "risk_score",
                "risk_level",
                "fraud_reasons"
            ]
        ].to_string(index=False)
    )

    save_fraud_alerts(result)