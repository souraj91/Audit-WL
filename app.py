import streamlit as st
import pandas as pd
import asyncio
import os
import sqlite3
import json
from playwright.async_api import async_playwright

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Ad-Crawler Pro", layout="wide")

# Installation de Playwright pour Streamlit Cloud
if not os.path.exists("/home/adminuser/.cache/ms-playwright"):
    try:
        os.system("playwright install chromium")
    except Exception as e:
        st.error(f"Erreur d'installation : {e}")

# --- LOGIQUE BASE DE DONNÉES ---
def init_db():
    conn = sqlite3.connect('audit_data.db')
    c = conn.cursor()
    # Correction de la syntaxe SQL ici
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

# --- MOTEUR DE CRAWLING ---
async def audit_site(url, browser, semaphore):
    async with semaphore:
        page = None
        try:
            clean_url = url.strip()
            full_url = clean_url if clean_url.startswith('http') else f'https://{clean_url}'
            page = await browser.new_page()
            await page.goto(full_url, timeout=60000, wait_until="networkidle")
            
            # Détection d'éléments
            ads = await page.query_selector_all("iframe[src*='ads'], [class*='ad-'], [id*='google_ads']")
            
            domains = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script[src]'))
                           .map(s => {
                               try { return new URL(s.src).hostname; }
                               catch(e) { return null; }
                           }).filter(h => h !== null)
            """)
            
            save_result(url, len(ads), list(set(domains)), "Success")
        except Exception as e:
            save_result(url, 0, [], f"Erreur: {str(e)}")
        finally:
            if page: await page.close()

# --- INTERFACE ---
init_db()
st.title("🕵️ Audit Publicitaire")

uploaded_file = st.file_uploader("Charger Excel", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    # On force les majuscules pour éviter le KeyError 'URL'
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    if 'URL' not in df.columns:
        st.error(f"Colonne 'URL' introuvable. Colonnes présentes : {list(df.columns)}")
    else:
        all_urls = df['URL'].dropna().unique().tolist()
        processed = get_processed_urls()
        remaining = [u for u in all_urls if u not in processed]

        st.metric("Sites restants", len(remaining))

        if st.button("🚀 Lancer l'audit"):
            p_bar = st.progress(0)
            async def run_process():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    semaphore = asyncio.Semaphore(5)
                    for i, url in enumerate(remaining):
                        await audit_site(url, browser, semaphore)
                        p_bar.progress((i + 1) / len(remaining))
                    await browser.close()
            asyncio.run(run_process())
            st.rerun()

    # Affichage des résultats
    conn = sqlite3.connect('audit_data.db')
    res_df = pd.read_sql("SELECT * FROM audit", conn)
    conn.close()
    if not res_df.empty:
        st.dataframe(res_df)
