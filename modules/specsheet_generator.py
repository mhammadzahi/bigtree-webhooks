import os
import re
import base64
import platform
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image

# Templating and PDF Generation
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from playwright.async_api import async_playwright
from woocommerce import API

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
        'leather': 'specsheet-template__LEATHER.html',
        'floor covering': 'specsheet-template__FLOOR_COVERING.html',
        'wallcovering': 'specsheet-template__WALL_COVERING.html',
        'wall covering': 'specsheet-template__WALL_COVERING.html',
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
        print("[DEBUG] Root category is 'furniture', checking subcategories")
        # Check subcategories for specific furniture types
        for cat in categories:
            cat_name = cat.get('name', '').lower()
            cat_slug = cat.get('slug', '').lower()
            print(f"[DEBUG] Checking subcategory: {cat_name} (slug: {cat_slug})")
            if any(k in cat_name or k in cat_slug for k in ['seating', 'chair', 'sofa', 'bench', 'stool']):
                print("[DEBUG] Matched seating furniture, returning FURNITURE_SEATING template")
                return 'specsheet-template__FURNITURE_SEATING.html'
        print("[DEBUG] No seating match, returning FURNITURE_OTHERS template")
        return 'specsheet-template__FURNITURE_OTHERS.html'

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
    Returns: HTML <img> tag string or empty string.
    """
    print("[DEBUG] process_image_to_base64 called")
    if not image_url:
        print("[DEBUG] No image URL provided")
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
        img.save(buffered, format="JPEG", quality=80)
        buffer_size = len(buffered.getvalue())
        print(f"[DEBUG] Image buffer size: {buffer_size} bytes ({buffer_size/1024:.2f} KB)")
        
        # Encode
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        print(f"[DEBUG] Base64 encoded string length: {len(img_str)} chars")
        
        # Return full HTML tag with styling to ensure it fits the container
        # utilizing object-fit: contain to keep aspect ratio inside the box
        print("[DEBUG] Returning Markup-wrapped image HTML")
        return Markup(f'<img src="data:image/jpeg;base64,{img_str}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; z-index: 1;" alt="Product Image" />')

    except Exception as e:
        print(f"  ❌ Image processing failed: {e}")
        print(f"[DEBUG] Exception type: {type(e).__name__}")
        return ""

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
    if wc_url and product.get('slug'):
        base = wc_url.rstrip('/')
        req_url = f"{base}/product/{product.get('slug')}/"
        print(f"[DEBUG] Request URL: {req_url}")
    else:
        print("[DEBUG] No WC URL or slug, using default request URL")

    # Context Mapping (matches placeholders in your HTML)
    context = {
        # Core
        'prdct_name': product.get('name', 'N/A'),
        'product_sku': product.get('sku', 'N/A'),
        'prdct_description': strip_html_tags(product.get('description', '')),
        
        # Categories
        'prdct_category': categories[0].get('name', 'N/A') if categories else 'N/A',
        'brand': brands[0].get('name', 'N/A') if brands else get_meta('brand'),

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
        'maintenance_and_care': get_meta('maintenance_&_care', clean=True),
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
            return value.replace('\n', '<br>\n')
        
        env.filters['nl2br'] = nl2br
        print("[DEBUG] Custom nl2br filter registered")
        
        print(f"[DEBUG] Loading template: {template_filename}")
        template = env.get_template(template_filename)
        print(f"[DEBUG] Template loaded, rendering with {len(context)} context variables")
        rendered_html = template.render(context)
        print(f"[DEBUG] HTML rendered successfully, length: {len(rendered_html)} chars")
        print("✓ HTML Rendered successfully")

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
            # Launch browser
            # args=['--no-sandbox'] is crucial for running as root/headless on Linux
            print("[DEBUG] Launching Chromium browser (headless)")
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            print("[DEBUG] Browser launched successfully")
            
            print("[DEBUG] Creating new page")
            page = await browser.new_page()
            print("[DEBUG] Page created")
            
            # Set content
            print("[DEBUG] Setting page content (waiting for networkidle)")
            await page.set_content(rendered_html, wait_until="networkidle")
            print("[DEBUG] Page content set, network idle")
            
            # Generate PDF
            # A4 dimensions are roughly 595px x 842px at 72dpi, but Playwright handles 'format="A4"' well
            # print_background=True ensures CSS background colors/images are visible
            print("[DEBUG] Generating PDF (A4 format, with background)")
            await page.pdf(
                path=output_pdf,
                format="A4",
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
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
