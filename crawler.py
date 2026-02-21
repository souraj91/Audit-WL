import asyncio
from playwright.async_api import async_playwright
from database import save_result

async def audit_site(url, browser, semaphore):
    async with semaphore:
        try:
            page = await browser.new_page()
            # On simule un utilisateur réel
            await page.goto(url, timeout=60000, wait_until="networkidle")
            
            # Détection des iframes et scripts de régies connues
            ads = await page.query_selector_all("iframe[src*='ads'], [class*='ad-']")
            
            # Extraction des domaines tiers
            domains = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script[src]'))
                           .map(s => new URL(s.src).hostname)
            """)
            
            save_result(url, len(ads), list(set(domains)), "Success")
            await page.close()
        except Exception as e:
            save_result(url, 0, [], f"Error: {str(e)}")
