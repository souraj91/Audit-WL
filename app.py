import streamlit as st
import pandas as pd
import asyncio
from crawler import audit_site
from database import init_db, get_processed_urls, update_ia_analysis
from playwright.async_api import async_playwright
import sqlite3

st.set_page_config(page_title="Ad-Crawler Pro", layout="wide")
init_db()

st.title("🕵️ Audit Publicitaire de Masse (1000+ sites)")

uploaded_file = st.file_uploader("Charger le fichier Excel", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    
    # --- CORRECTIF KEYERROR ---
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    if 'URL' not in df.columns:
        st.error(f"Colonne 'URL' manquante. Colonnes trouvées : {list(df.columns)}")
    else:
        all_urls = df['URL'].dropna().tolist()
        processed = get_processed_urls()
        remaining = [u for u in all_urls if u not in processed]

        col1, col2, col3 = st.columns(3)
        col1.metric("Total sites", len(all_urls))
        col2.metric("Déjà scannés", len(processed))
        col3.metric("Restants", len(remaining))

        if st.button("🚀 Lancer / Reprendre l'audit"):
            if not remaining:
                st.success("Tous les sites ont déjà été traités.")
            else:
                progress_text = st.empty()
                bar = st.progress(0)
                
                async def main():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        semaphore = asyncio.Semaphore(5) # Prudence : 5 sites simultanés
                        
                        for i, url in enumerate(remaining):
                            progress_text.text(f"Analyse de {url} ({i+1}/{len(remaining)})")
                            await audit_site(url, browser, semaphore)
                            bar.progress((i + 1) / len(remaining))
                        
                        await browser.close()

                asyncio.run(main())
                st.success("Scan terminé ! Rechargez la page pour voir les données.")

        # Affichage des résultats
        if st.checkbox("Voir les résultats bruts"):
            conn = sqlite3.connect('audit_data.db')
            res_df = pd.read_sql("SELECT * FROM audit", conn)
            st.dataframe(res_df)
            
            st.download_button("Télécharger CSV", res_df.to_csv(), "export_audit.csv")
