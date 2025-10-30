import time
from playwright.sync_api import sync_playwright, Error

def create_pdf_from_url(url, output_path):

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. Emulate a common screen size for consistent layout
        page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            # 2. Go to the URL and wait for the page to be 'almost' ready
            # 'domcontentloaded' is often a good starting point
            page.goto(url, wait_until='domcontentloaded', timeout=60000) # Increased timeout for heavy pages

            # 3. Emulate the 'screen' media type. This is CRITICAL.
            # This tells the browser to use the CSS for screen viewing, not printing.
            # This usually fixes the "destroyed layout" and "visible links" issues.
            page.emulate_media(media='screen')

            # 4. Scroll to the bottom of the page to trigger lazy-loaded elements
            print("Scrolling to trigger lazy-loading...")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            # 5. Wait for network requests to finish AND add a small manual delay
            # This gives time for images and fonts to load after scrolling
            page.wait_for_load_state('networkidle')
            time.sleep(3) # A 3-second buffer for rendering to settle

            print("Generating PDF...")
            # 6. Generate the PDF with better options
            page.pdf(
                path=output_path,
                format='A4',
                print_background=True,  # Ensures background colors and images are included
                margin={"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"},
                scale=0.8 # You can adjust the scale to fit content better on the page
            )

        except Exception as e:
            print(f"An error occurred: {e}")
            
        finally:
            browser.close()

