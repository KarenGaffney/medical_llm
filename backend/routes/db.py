import os
import pyodbc
from flask import Flask, app, request, jsonify
import requests


def get_conn():
    server = os.getenv("AZURE_SQL_SERVER")         
    db = os.getenv("AZURE_SQL_DB")
    user = os.getenv("AZURE_SQL_USER")
    pwd = os.getenv("AZURE_SQL_PASSWORD")
    print("SERVER:", server, "DB:", db, flush=True)

    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"UID={user};PWD={pwd};"
        "Encrypt=yes;TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

def lookup_patient_email(full_name: str):
    with get_conn() as conn:
        try: 
            cur = conn.cursor()
            cur.execute("SELECT TOP 1 Email FROM dbo.Patients WHERE FullName = ?", full_name)
            row = cur.fetchone()
            return row[0] if row else None
        except Exception as e:
            print("Error looking up patient email:", e, flush=True)
            raise

def add_patient(name: str, email: str, phone: str = None, dob: str = None):
    with get_conn() as conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO dbo.Patients (FullName, Email, Phone, DOB) VALUES (?, ?, ?, ?)",
                name, email, phone, dob
            )
            conn.commit()
            return 
        except Exception as e:
            print("Error adding patient:", e, flush=True)
            raise
    
