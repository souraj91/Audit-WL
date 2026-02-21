import streamlit as st
import pandas as pd
import asyncio
from crawler import audit_site
from database import init_db, get_processed_urls
from playwright.async_api import async_playwright
from mistralai.client import MistralClient

st.set_page_config(page_title="Industrial Ad Auditor", layout="wide")
init_db()

st.title("🚀 Audit Publicitaire Haute Performance")

uploaded_file = st.file_uploader("Importer votre liste Excel (colonne 'URL')", type="xlsx")

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    all_urls = df['URL'].tolist()
    processed = get_processed_urls()
    remaining_urls = [u for u in all_urls if u not in processed]

    st.info(f"Total: {len(all_urls)} | Déjà traités: {len(processed)} | Restants: {len(remaining_urls)}")

    if st.button("Démarrer / Reprendre l'Audit"):
        progress_bar = st.progress(0)
        
        async def run_bulk():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                semaphore = asyncio.Semaphore(10) # 10 sites en parallèle
                
                tasks = [audit_site(url, browser, semaphore) for url in remaining_urls]
                for i, task in enumerate(asyncio.as_completed(tasks)):
                    await task
                    progress_bar.progress((i + 1) / len(remaining_urls))
                
                await browser.close()

        asyncio.run(run_bulk())
        st.success("Audit terminé !")

    # Bouton pour l'analyse IA avec Mistral sur les résultats stockés en DB
    if st.button("Enrichir avec Mistral AI"):
        st.write("Analyse sémantique des régies en cours...")
        # Logique Mistral ici sur les domaines uniques stockés en DB
