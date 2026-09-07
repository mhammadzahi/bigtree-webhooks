import os
import re
import base64
import platform
import requests
import subprocess
import stat
from io import BytesIO
from datetime import datetime
from PIL import Image

# Templating and PDF Generation
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from playwright.async_api import async_playwright
from woocommerce import API
from modules.woocommerce_service import generate_woo_external_cart_url
from modules.utm import build_template_utm, inject_utm_into_html

# --- CONFIGURATION ---
TEMPLATE_DIR = 'files'
TEMP_DIR = 'files/temp'
os.makedirs(TEMP_DIR, exist_ok=True)

# Global WooCommerce API instance
wcapi = None

def init_woocommerce_api(url, consumer_key, consumer_secret):
    """Initialize WooCommerce API with provided credentials"""
    print("[DEBUG] init_woocommerce_api called")
    print(f"[DEBUG] URL: {url}")
    global wcapi
    if wcapi is None:
        print("[DEBUG] Initializing new WooCommerce API instance")
        wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=10
        )
        print("[DEBUG] WooCommerce API initialized successfully")
    else:
        print("[DEBUG] WooCommerce API already initialized, reusing instance")
    return wcapi

def strip_html_tags(text):
    """Clean HTML tags but preserve basic line breaks for text rendering"""
    if not text:
        print("[DEBUG] strip_html_tags: Empty text received")
        return ''
    
    print(f"[DEBUG] strip_html_tags: Input length: {len(text)} chars")
    
    # 1. Convert structural breaks to newlines
    clean = re.sub(r'<br\s*/?>', '\n', text)
    clean = re.sub(r'</p>\s*<p>', '\n\n', clean)
    clean = re.sub(r'<[^>]+>', '', clean)  # Strip remaining tags
    
    # 2. Decode entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    clean = clean.replace('&quot;', '"')
    clean = clean.replace('&apos;', "'")
    
    # 3. Normalize whitespace
    clean = clean.replace('\r\n', '\n').replace('\r', '\n')
    clean = re.sub(r' +', ' ', clean)       # Multiple spaces -> single space
    clean = re.sub(r'\n{3,}', '\n\n', clean) # Max 2 newlines
    
    result = clean.strip()
    print(f"[DEBUG] strip_html_tags: Output length: {len(result)} chars")
    return result

def get_root_parent_category(category_id):
    """Recursively find the root parent category via WooCommerce API"""
    print(f"[DEBUG] get_root_parent_category: Fetching category ID: {category_id}")
    global wcapi
    if wcapi is None:
        print("  ⚠️ WooCommerce API not initialized")
        return None
    
    try:
        print(f"[DEBUG] Making API request for category {category_id}")
        response = wcapi.get(f"products/categories/{category_id}")
        print(f"[DEBUG] API response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[DEBUG] Non-200 status code received: {response.status_code}")
            return None
            
        category = response.json()
        parent_id = category.get('parent', 0)
        print(f"[DEBUG] Category: {category.get('name')}, Parent ID: {parent_id}")
        
        if parent_id == 0:
            print(f"  ✓ Found root category: {category.get('name')}")
            return category
        
        print(f"[DEBUG] Recursing to parent category: {parent_id}")
        return get_root_parent_category(parent_id)
    except Exception as e:
        print(f"  ❌ Error fetching category hierarchy: {e}")
        return None

def get_template_by_category(product, wc_url=None, wc_key=None, wc_secret=None):
    """
    Selects the correct HTML template based on product category.
    """
    print("[DEBUG] get_template_by_category called")
    print(f"[DEBUG] Product: {product.get('name', 'Unknown')} (ID: {product.get('id', 'N/A')})")
    
    if wc_url and wc_key and wc_secret:
        print("[DEBUG] WooCommerce credentials provided, initializing API")
        init_woocommerce_api(wc_url, wc_key, wc_secret)
    
    categories = product.get('categories', [])
    print(f"[DEBUG] Product has {len(categories)} categories")
    
    # Fallback default
    default_template = 'specsheet-template__ALL.html'
    
    if not categories:
        print("[DEBUG] No categories found, using default template")
        return default_template

    # Known mappings (Root Category Name -> Filename)
    # Ensure these files exist in the 'files/' directory
    known_templates = {
        'fabric': 'specsheet-template__FABRIC.html',
        'fabrics': 'specsheet-template__FABRIC.html',
        'leather': 'specsheet-template__LEATHER.html',
        'leathers': 'specsheet-template__LEATHER.html',
        'floor covering': 'specsheet-template__FLOOR_COVERING.html',
        'floor coverings': 'specsheet-template__FLOOR_COVERING.html',
        'wallcovering': 'specsheet-template__WALL_COVERING.html',
        'wallcoverings': 'specsheet-template__WALL_COVERING.html',
        'wall covering': 'specsheet-template__WALL_COVERING.html',
        'wall coverings': 'specsheet-template__WALL_COVERING.html',
        'fine art': 'specsheet-template__FINE_ART.html',
        'lighting': 'specsheet-template__LIGHTING.html',
        'objects': 'specsheet-template__OBJECTS.html',
        # Furniture is handled dynamically below
    }

    # 1. Find Root Category
    first_cat_id = categories[0].get('id')
    print(f"[DEBUG] First category ID: {first_cat_id}")
    root_category = get_root_parent_category(first_cat_id)
    
    if not root_category:
        print("[DEBUG] Could not find root category, using default template")
        return default_template
        
    root_name = root_category.get('name', '').lower()
    print(f"[DEBUG] Root category name: {root_name}")
    
    # 2. Special Logic for Furniture
    if root_name == 'furniture':
        print("[DEBUG] Root category is 'furniture', returning merged FURNITURE template")
        return 'specsheet-template__FURNITURE.html'

    # 3. Check Standard Mappings
    if root_name in known_templates:
        template = known_templates[root_name]
        print(f"[DEBUG] Found template mapping: {root_name} -> {template}")
        return template

    print(f"[DEBUG] No template mapping found for '{root_name}', using default")
    return default_template

def process_image_to_base64(image_url):
    """
    Downloads image, resizes if too large, and converts to Base64 string.
    Returns: HTML <img> tag string or empty string if image unavailable.
    Always returns safely without breaking the PDF generation.
    """
    print("[DEBUG] process_image_to_base64 called")
    if not image_url:
        print("[DEBUG] No image URL provided, returning empty string (will show fallback in template)")
        return ""

    try:
        print(f"  Processing image: {image_url}")
        response = requests.get(image_url, timeout=10)
        print(f"[DEBUG] Image download status: {response.status_code}")
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        print(f"[DEBUG] Image opened: {img.width}x{img.height}, mode: {img.mode}")
        
        # Convert to RGB to avoid mode issues (e.g. CMYK/RGBA)
        if img.mode not in ('RGB', 'L'):
            print(f"[DEBUG] Converting image from {img.mode} to RGB")
            img = img.convert('RGB')

        # Limit max dimensions to reduce PDF size (max 800px for better performance)
        max_dimension = 800
        if img.height > max_dimension or img.width > max_dimension:
            original_size = (img.width, img.height)
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            print(f"[DEBUG] Image resized from {original_size} to {img.width}x{img.height}")

        # Save to buffer as JPEG
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        buffer_size = len(buffered.getvalue())
        print(f"[DEBUG] Image buffer size: {buffer_size} bytes ({buffer_size/1024:.2f} KB)")
        
        # Encode
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        print(f"[DEBUG] Base64 encoded string length: {len(img_str)} chars")
        
        # Return full HTML tag with proper styling for PDF rendering
        # Using absolute positioning to fill the container properly
        html_img = Markup(
            f'<img src="data:image/jpeg;base64,{img_str}" '
            f'style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; '
            f'object-fit: contain; z-index: 1;" alt="Product Image" />'
        )
        print("[DEBUG] Returning Markup-wrapped image HTML")
        return html_img

    except Exception as e:
        print(f"  ⚠️ Image processing failed: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        print(f"[DEBUG] PDF will render with empty image placeholder (template will show fallback text)")
        return ""

async def _launch_browser_with_fallback(p):
    """
    Launch Chromium browser with fallback handling for permission issues.
    Takes Playwright instance as parameter.
    Attempts to:
    1. Fix permissions on Playwright's Chromium binary
    2. Use system Chromium if available
    3. Launch with various flag combinations
    """
    browser = None
    last_error = None
    
    # Try 1: Standard launch with no-sandbox
    try:
        print("[DEBUG] Attempt 1: Launching Chromium with --no-sandbox")
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        print("[DEBUG] Browser launched successfully on attempt 1")
        return browser
    except Exception as e:
        last_error = e
        print(f"[DEBUG] Attempt 1 failed: {type(e).__name__}")
    
    # Try 2: Fix Playwright binary permissions and retry
    if "EACCES" in str(last_error) or "spawn" in str(last_error):
        try:
            print("[DEBUG] Attempt 2: Fixing Playwright binary permissions")
            playwright_cache = os.path.expanduser("~/.cache/ms-playwright")
            if os.path.exists(playwright_cache):
                # Find and fix permissions on chrome-headless-shell binaries
                for root, dirs, files in os.walk(playwright_cache):
                    for file in files:
                        if 'chrome-headless-shell' in file:
                            filepath = os.path.join(root, file)
                            try:
                                st = os.stat(filepath)
                                # Add execute permission
                                os.chmod(filepath, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                                print(f"[DEBUG] Fixed permissions on {filepath}")
                            except Exception as perm_error:
                                print(f"[DEBUG] Could not fix permissions on {filepath}: {perm_error}")
            
            # Retry launch after fixing permissions
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            print("[DEBUG] Browser launched successfully on attempt 2 (after fixing permissions)")
            return browser
        except Exception as e:
            last_error = e
            print(f"[DEBUG] Attempt 2 failed: {type(e).__name__}")
    
    # Try 3: Use system Chromium if installed (on Linux)
    if platform.system() == "Linux":
        try:
            print("[DEBUG] Attempt 3: Launching with system Chromium")
            browser = await p.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium-browser",
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            print("[DEBUG] Browser launched successfully with system Chromium")
            return browser
        except Exception as e:
            print(f"[DEBUG] Attempt 3 failed (system Chromium not found or not executable)")
            last_error = e
    
    # Try 4: Minimal args
    try:
        print("[DEBUG] Attempt 4: Launching with minimal arguments")
        browser = await p.chromium.launch(headless=True)
        print("[DEBUG] Browser launched successfully with minimal args")
        return browser
    except Exception as e:
        last_error = e
        print(f"[DEBUG] Attempt 4 failed: {type(e).__name__}")
    
    # All attempts failed
    raise RuntimeError(
        f"Failed to launch Chromium browser after 4 attempts. "
        f"Last error: {last_error}\n"
        f"SOLUTION: Run 'python -m playwright install --with-deps chromium' on the server."
    )

async def generate_specsheet_pdf(product, wc_url=None, wc_key=None, wc_secret=None):
    print("\n" + "="*50)
    print(f"STARTING PDF GENERATION (Playwright): {product.get('name')}")
    print("="*50)

    # 1. Determine Template
    template_filename = get_template_by_category(product, wc_url, wc_key, wc_secret)
    print(f"Selected Template: {template_filename}")

    # 2. Prepare Data Context
    print("[DEBUG] Preparing data context")
    meta_data = product.get('meta_data', [])
    categories = product.get('categories', [])
    brands = product.get('brands', [])
    images = product.get('images', [])
    
    print(f"[DEBUG] Product has {len(meta_data)} meta fields")
    print(f"[DEBUG] Product has {len(categories)} categories")
    print(f"[DEBUG] Product has {len(brands)} brands")
    print(f"[DEBUG] Product has {len(images)} images")

    def get_meta(key, default='N/A', clean=False):
        for item in meta_data:
            if item.get('key') == key:
                val = item.get('value')
                if val:
                    result = strip_html_tags(val) if clean else val
                    print(f"[DEBUG] get_meta('{key}'): Found value (length: {len(str(result))})")
                    return result
        print(f"[DEBUG] get_meta('{key}'): Not found, using default")
        return default

    # Handle Image
    image_url = images[0].get('src') if images else None
    print(f"[DEBUG] Image URL: {image_url}")
    image_html = process_image_to_base64(image_url)
    print(f"[DEBUG] Image HTML prepared: {len(str(image_html)) if image_html else 0} chars")

    # Handle Inquiry URL
    req_url = 'N/A'
    if wc_url and product.get('id'):
        req_url = generate_woo_external_cart_url(wc_url, product.get('id'))
        print(f"[DEBUG] Request URL: {req_url}")
    else:
        print("[DEBUG] No WC URL or product ID, using default request URL")

    # Build product full URL for 'more info' links
    product_slug = product.get('slug', '')
    domain = wc_url.rstrip('/') if wc_url else ''
    product_full_url = f"{domain}/{product_slug}" if domain and product_slug else ''
    print(f"[DEBUG] Product full URL: {product_full_url}")

    _more_info_link = (
        f' <a href="{product_full_url}" '
        f'style="color: #F65C0D; font-weight: bold; text-decoration: none;">. . . <span style="text-decoration: underline;">more info.</span></a>'
        if product_full_url else ' . . . more info.'
    )

    def smart_truncate(text, base_limit, tolerance=10):
        """
        Soft-cut truncation that avoids splitting words mid-way.

        Steps:
          1. Return the full string unchanged if it fits within base_limit.
          2. Search forward up to `tolerance` characters past base_limit for
             the first space — truncate there (completing the current word).
          3. If no space exists in the forward buffer, search backwards from
             base_limit for the last space — truncate there instead.
          4. Append the more-info hyperlink to whichever cut point is chosen.

        Args:
            text (str):       Clean (HTML-stripped) input string.
            base_limit (int): Preferred maximum character count.
            tolerance (int):  Extra characters to scan forward for a word boundary.

        Returns:
            str: Truncated string with appended hyperlink, or original string.
        """
        if len(text) <= base_limit:
            return text

        # --- Forward scan: look for a space in [base_limit, base_limit + tolerance] ---
        forward_window = text[base_limit : base_limit + tolerance]  # safe even if text is short
        space_forward = forward_window.find(' ')

        if space_forward != -1:
            # Found a space in the forward buffer — cut right after the completed word
            cut_index = base_limit + space_forward
        else:
            # --- Backward scan: find the last space before base_limit ---
            space_backward = text.rfind(' ', 0, base_limit)
            if space_backward != -1:
                cut_index = space_backward
            else:
                # No spaces at all — fall back to a hard cut at base_limit
                cut_index = base_limit

        return text[:cut_index] + _more_info_link

    # Truncate Description (base 380, tolerance +10)
    _raw_description = strip_html_tags(product.get('description', ''))
    _truncated_description = smart_truncate(_raw_description, base_limit=380, tolerance=10)
    if _truncated_description is not _raw_description:
        print(f"[DEBUG] Description soft-truncated at word boundary (original: {len(_raw_description)} chars)")
    prdct_description = Markup(_truncated_description)

    # Truncate Maintenance & Care (base 300, tolerance +10)
    _raw_maintenance = strip_html_tags(get_meta('maintenance_&_care', default='', clean=False))
    # print(_raw_maintenance)
    _truncated_maintenance = smart_truncate(_raw_maintenance, base_limit=300, tolerance=10)
    if _truncated_maintenance is not _raw_maintenance:
        print(f"[DEBUG] Maintenance & Care soft-truncated at word boundary (original: {len(_raw_maintenance)} chars)")
    maintenance_and_care = Markup(re.sub(r'\n+', '<br>', _truncated_maintenance))

    # Context Mapping (matches placeholders in your HTML)
    context = {
        # Core
        'prdct_name': Markup(strip_html_tags(product.get('name', 'N/A'))),
        'product_sku': product.get('sku', 'N/A'),
        'prdct_description': prdct_description,
        
        # Categories
        'prdct_category': Markup(strip_html_tags(categories[0].get('name', 'N/A') if categories else 'N/A')),
        'brand': Markup(strip_html_tags(brands[0].get('name', 'N/A') if brands else get_meta('brand'))),

        # Image
        'IMAGE_PLACEHOLDER': image_html,  # Injects the <img ...> tag
        
        # Links
        'REQUEST_INQUIRY_URL': req_url,

        # Product Specs (Meta)
        'type': get_meta('type'),
        'width': get_meta('width'),
        'length': get_meta('length'),
        'size': get_meta('size'),
        'thickness': get_meta('thickness'),
        'weight': get_meta('weight'),
        'color': get_meta('color'),
        'origin': get_meta('origin'),
        'composition': get_meta('composition'),
        'backing': get_meta('backing'),
        'pattern': get_meta('pattern'),
        'repeat': get_meta('repeat'),

        # Furniture Specific
        'armrest_height': get_meta('armrest_height'),
        'seat_height': get_meta('seat_height'),
        'seat_depth': get_meta('seat_depth'),
        'primary_material': get_meta('primary_material'),
        'primary_finish': get_meta('primary_finish'),
        'secondary_material': get_meta('secondary_material'),
        'secondary_finish': get_meta('secondary_finish'),
        'fabric': get_meta('fabric'),
        'fabric_composition': get_meta('fabric_composition'),
        'seat_filling': get_meta('seat_filling'),
        'back_filling': get_meta('back_filling'),
        
        # Usage
        'application': get_meta('application'),
        'environment': get_meta('environment'),
        'project': get_meta('project', clean=True),
        
        # Technical
        'durability': get_meta('durability'),
        'piling': get_meta('piling'),
        'color_resistance': get_meta('color_resistance'),
        'color_fastness': get_meta('color_fastness', clean=True),
        'seam_slippage': get_meta('seam_slippage'),
        'shrinkage_wet': get_meta('shrinkage_wet'),
        'flame_retardant': get_meta('flame_retardant', clean=True),
        'structural_compliance': get_meta('structural_compliance'),
        'thermal_resistance': get_meta('thermal_resistance'),
        'weather_resistance': get_meta('weather_resistance'),
        'antibacterial': get_meta('antibacterial'),
        'other_certifications': get_meta('other_certifications'),
        
        # Care & Commercial
        'maintenance_and_care': maintenance_and_care,
        'warranty': get_meta('warranty'),
        'minimum_order_quantity': get_meta('minimum_order_quantity'),
        'lead_time': get_meta('lead_time'),
        'price_tier': get_meta('price_tier'),
        'note': get_meta('note'),
    }

    # 3. Render HTML with Jinja2
    print("[DEBUG] Starting HTML rendering with Jinja2")
    try:
        print(f"[DEBUG] Template directory: {TEMPLATE_DIR}")
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        print("[DEBUG] Jinja2 environment created")
        
        # Custom filter to turn newlines into <br> for descriptions
        def nl2br(value):
            if not value: return ""
            import re
            value = re.sub(r'\n{2,}', '\n', value)
            return value.replace('\n', '<br>\n')
        
        env.filters['nl2br'] = nl2br
        print("[DEBUG] Custom nl2br filter registered")
        
        print(f"[DEBUG] Loading template: {template_filename}")
        template = env.get_template(template_filename)
        print(f"[DEBUG] Template loaded, rendering with {len(context)} context variables")
        rendered_html = template.render(context)
        print(f"[DEBUG] HTML rendered successfully, length: {len(rendered_html)} chars")
        print("✓ HTML Rendered successfully")

        # Category-specific UTM tagging: append utm_* params to every
        # bigtree-group.com link (footer, inquiry/add-to-cart, product "more info")
        # so GA4 can attribute PDF-driven traffic to this product category.
        utm = build_template_utm(template_filename)
        if utm:
            rendered_html, utm_count, utm_sample = inject_utm_into_html(rendered_html, utm)
            print(f"[UTM] Tagged {utm_count} bigtree-group.com link(s) "
                  f"(campaign={utm['utm_campaign']}). Sample: {utm_sample}")
        else:
            print(f"[UTM] No UTM mapping for '{template_filename}', links left untagged")

    except Exception as e:
        print(f"❌ Template Rendering Failed: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        # Return None or raise logic here depending on preference
        raise RuntimeError(f"Template rendering failed: {e}")

    # 4. Generate PDF with Playwright
    output_pdf = os.path.join(TEMP_DIR, f"{product['id']}_specsheet.pdf")
    print(f"[DEBUG] Output PDF path: {output_pdf}")
    
    try:
        print("[DEBUG] Starting Playwright async context")
        async with async_playwright() as p:
            # Launch browser with fallback handling for permission issues
            print("[DEBUG] Launching Chromium browser (with fallback support)")
            browser = await _launch_browser_with_fallback(p)
            print("[DEBUG] Browser launched successfully")
            
            print("[DEBUG] Creating new page")
            # Set viewport to A4 dimensions in pixels at 96dpi (standard screen DPI)
            # A4 = 210mm x 297mm = 794px x 1123px at 96dpi
            page = await browser.new_page(viewport={"width": 794, "height": int(1123 * 2)})
            print("[DEBUG] Page created with A4-extended viewport for proper scaling")
            
            # Set content
            print("[DEBUG] Setting page content (waiting for networkidle)")
            await page.set_content(rendered_html, wait_until="networkidle")
            print("[DEBUG] Page content set, network idle")
            
            # Set A4 page size and margins for print
            print("[DEBUG] Generating PDF (A4 format, with full background rendering)")
            await page.pdf(
                path=output_pdf,
                format="A4",
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
                scale=1.0,
                prefer_css_page_size=True
            )
            print("[DEBUG] PDF generated successfully")
            
            print("[DEBUG] Closing browser")
            await browser.close()
            print("[DEBUG] Browser closed")
            
        print(f"✅ PDF Generated: {output_pdf}")
        if os.path.exists(output_pdf):
            file_size = os.path.getsize(output_pdf)
            print(f"[DEBUG] PDF file size: {file_size} bytes ({file_size/1024:.2f} KB)")
        return output_pdf

    except Exception as e:
        print(f"❌ PDF Generation Failed: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        raise RuntimeError(f"Playwright PDF generation failed: {e}")

# Note: No cleanup of the PDF is done here; the calling function in app.py handles deletion.
