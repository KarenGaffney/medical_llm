import os
import pyodbc

def get_conn():
    server = os.getenv("AZURE_SQL_SERVER")         
    db = os.getenv("AZURE_SQL_DB")
    user = os.getenv("AZURE_SQL_USER")
    pwd = os.getenv("AZURE_SQL_PASSWORD")

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"UID={user};PWD={pwd};"
        "Encrypt=yes;TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

def lookup_patient_email(full_name: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT TOP 1 Email FROM dbo.Patients WHERE FullName = ?", full_name)
        row = cur.fetchone()
        return row[0] if row else None
