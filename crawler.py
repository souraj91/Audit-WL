import asyncio
from playwright.async_api import async_playwright
from database import save_result

async def audit_site(url, browser, semaphore):
    async with semaphore:
        page = None
        try:
            # Nettoyage URL
            full_url = url if url.startswith('http') else f'https://{url}'
            page = await browser.new_page()
            
            # Navigation avec timeout
            await page.goto(full_url, timeout=45000, wait_until="networkidle")
            
            # Détection des encarts publicitaires via sélecteurs communs
            ads = await page.query_selector_all("iframe[src*='ads'], [class*='ad-'], [id*='google_ads']")
            
            # Extraction des domaines tiers (scripts)
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
