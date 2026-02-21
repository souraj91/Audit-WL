import sqlite3
import json

def init_db():
    conn = sqlite3.connect('audit_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audit 
                 (url TEXT PRIMARY KEY, ads_count INTEGER, domains TEXT, status TEXT, ia_analysis TEXT)''')
    conn.commit()
    conn.close()

def save_result(url, ads_count, domains, status):
    conn = sqlite3.connect('audit_data.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO audit (url, ads_count, domains, status) VALUES (?, ?, ?, ?)", 
              (url, ads_count, json.dumps(domains), status))
    conn.commit()
    conn.close()

def get_processed_urls():
    conn = sqlite3.connect('audit_data.db')
    c = conn.cursor()
    c.execute("SELECT url FROM audit")
    urls = [row[0] for row in c.fetchall()]
    conn.close()
    return urls

def update_ia_analysis(url, analysis_json):
    conn = sqlite3.connect('audit_data.db')
    c = conn.cursor()
    c.execute("UPDATE audit SET ia_analysis = ? WHERE url = ?", (analysis_json, url))
    conn.commit()
    conn.close()
