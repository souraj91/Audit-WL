import streamlit as st
import pandas as pd
import asyncio
import os
import sqlite3
import json
from playwright.async_api import async_playwright
from mistralai.client import MistralClient

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Ad-Crawler Pro", layout="wide")

# 1. Installation forcée de Playwright pour Streamlit Cloud
if not os.path.exists("/home/adminuser/.cache/ms-playwright"):
    try:
        os.system("playwright install chromium")
    except Exception as e:
        st.error(f"Erreur d'installation des navigateurs : {e}")

# --- LOGIQUE BASE DE DONNÉES ---
def init_db():
    conn = sqlite3.connect('audit_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audit 
                 (url TEXT PRIMARY KEY, ads_count INTEGER, domains TEXT, status TEXT, ia_analysis TEXT)'' Row)
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
            # Nettoyage et formatage URL
            clean_url = url.strip()
            full_url = clean_url if clean_url.startswith('http') else f'https://{clean_url}'
            
            page = await browser.new_page()
            # Navigation avec timeout généreux
            await page.goto(full_url, timeout=60000, wait_until="networkidle")
            
            # Détection des éléments publicitaires (Sélecteurs classiques)
            ads = await page.query_selector_all("iframe[src*='ads'], [class*='ad-'], [id*='google_ads']")
            
            # Extraction des domaines tiers (scripts externes)
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
            if page:
                await page.close()

# --- INTERFACE STREAMLIT ---
init_db()
st.title("🕵️ Audit Publicitaire Haute Performance")
st.markdown("Analyse de masse via Playwright & Stockage SQLite")

uploaded_file = st.file_uploader("Charger votre fichier Excel", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # --- CORRECTIF KEYERROR ---
    # Nettoie les noms de colonnes (Majuscules + Suppression espaces)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    if 'URL' not in df.columns:
        st.error(f"❌ Colonne 'URL' manquante. Colonnes détectées : {list(df.columns)}")
        st.info("Vérifiez que votre fichier contient une colonne nommée 'URL' ou 'url'.")
    else:
        all_urls = df['URL'].dropna().unique().tolist()
        processed = get_processed_urls()
        remaining = [u for u in all_urls if u not in processed]

        # Tableau de bord
        c1, c2, c3 = st.columns(3)
        c1.metric("Cibles totales", len(all_urls))
        c2.metric("Déjà analysés", len(processed))
        c3.metric("Restants", len(remaining))

        # --- BOUTON DE LANCEMENT ---
        if st.button("🚀 Démarrer l'audit de masse"):
            if not remaining:
                st.success("Tous les sites ont déjà été traités ! Consultez les résultats ci-dessous.")
            else:
                p_bar = st.progress(0)
                status_text = st.empty()
                
                async def run_process():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        semaphore = asyncio.Semaphore(5) # Limite à 5 sites à la fois
                        
                        for i, url in enumerate(remaining):
                            status_text.text(f"Traitement de : {url} ({i+1}/{len(remaining)})")
                            await audit_site(url, browser, semaphore)
                            p_bar.progress((i + 1) / len(remaining))
                        
                        await browser.close()

                asyncio.run(run_process())
                st.success("✅ Audit terminé !")
                st.rerun()

    # --- AFFICHAGE & EXPORT ---
    st.divider()
    st.subheader("📊 Résultats de l'audit")
    
    conn = sqlite3.connect('audit_data.db')
    final_df = pd.read_sql("SELECT * FROM audit", conn)
    conn.close()

    if not final_df.empty:
        st.dataframe(final_df, use_container_width=True)
        
        # Export Excel / CSV
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger le rapport (CSV)",
            data=csv,
            file_name='rapport_audit_publicitaire.csv',
            mime='text/csv',
        )
    else:
        st.info("Aucun résultat disponible pour le moment. Lancez l'audit.")
