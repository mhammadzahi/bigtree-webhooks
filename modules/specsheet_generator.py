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
    global wcapi
    if wcapi is None:
        wcapi = API(
            url=url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=10
        )
    return wcapi

def strip_html_tags(text):
    """Clean HTML tags but preserve basic line breaks for text rendering"""
    if not text:
        return ''
    
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
    
    return clean.strip()

def get_root_parent_category(category_id):
    """Recursively find the root parent category via WooCommerce API"""
    global wcapi
    if wcapi is None:
        print("  ⚠️ WooCommerce API not initialized")
        return None
    
    try:
        response = wcapi.get(f"products/categories/{category_id}")
        if response.status_code != 200:
            return None
            
        category = response.json()
        parent_id = category.get('parent', 0)
        
        if parent_id == 0:
            print(f"  ✓ Found root category: {category.get('name')}")
            return category
        
        return get_root_parent_category(parent_id)
    except Exception as e:
        print(f"  ❌ Error fetching category hierarchy: {e}")
        return None

def get_template_by_category(product, wc_url=None, wc_key=None, wc_secret=None):
    """
    Selects the correct HTML template based on product category.
    """
    if wc_url and wc_key and wc_secret:
        init_woocommerce_api(wc_url, wc_key, wc_secret)
    
    categories = product.get('categories', [])
    
    # Fallback default
    default_template = 'specsheet-template__ALL.html'
    
    if not categories:
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
    root_category = get_root_parent_category(first_cat_id)
    
    if not root_category:
        return default_template
        
    root_name = root_category.get('name', '').lower()
    
    # 2. Special Logic for Furniture
    if root_name == 'furniture':
        # Check subcategories for specific furniture types
        for cat in categories:
            cat_name = cat.get('name', '').lower()
            cat_slug = cat.get('slug', '').lower()
            if any(k in cat_name or k in cat_slug for k in ['seating', 'chair', 'sofa', 'bench', 'stool']):
                return 'specsheet-template__FURNITURE_SEATING.html'
        return 'specsheet-template__FURNITURE_OTHERS.html'

    # 3. Check Standard Mappings
    if root_name in known_templates:
        return known_templates[root_name]

    return default_template

def process_image_to_base64(image_url):
    """
    Downloads image, resizes if too large, and converts to Base64 string.
    Returns: HTML <img> tag string or empty string.
    """
    if not image_url:
        return ""

    try:
        print(f"  Processing image: {image_url}")
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        
        # Convert to RGB to avoid mode issues (e.g. CMYK/RGBA)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Limit max dimensions to reduce PDF size (max 800px for better performance)
        max_dimension = 800
        if img.height > max_dimension or img.width > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        # Save to buffer as JPEG
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        
        # Encode
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Return full HTML tag with styling to ensure it fits the container
        # utilizing object-fit: contain to keep aspect ratio inside the box
        return f'<img src="data:image/jpeg;base64,{img_str}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; z-index: 1;" alt="Product Image" />'

    except Exception as e:
        print(f"  ❌ Image processing failed: {e}")
        return ""

async def generate_specsheet_pdf(product, wc_url=None, wc_key=None, wc_secret=None):
    print("\n" + "="*50)
    print(f"STARTING PDF GENERATION (Playwright): {product.get('name')}")
    print("="*50)

    # 1. Determine Template
    template_filename = get_template_by_category(product, wc_url, wc_key, wc_secret)
    print(f"Selected Template: {template_filename}")

    # 2. Prepare Data Context
    meta_data = product.get('meta_data', [])
    categories = product.get('categories', [])
    brands = product.get('brands', [])
    images = product.get('images', [])

    def get_meta(key, default='N/A', clean=False):
        for item in meta_data:
            if item.get('key') == key:
                val = item.get('value')
                if val:
                    return strip_html_tags(val) if clean else val
        return default

    # Handle Image
    image_url = images[0].get('src') if images else None
    image_html = process_image_to_base64(image_url)

    # Handle Inquiry URL
    req_url = 'N/A'
    if wc_url and product.get('slug'):
        base = wc_url.rstrip('/')
        req_url = f"{base}/product/{product.get('slug')}/"

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
    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Custom filter to turn newlines into <br> for descriptions
        def nl2br(value):
            if not value: return ""
            return value.replace('\n', '<br>\n')
        
        env.filters['nl2br'] = nl2br
        
        template = env.get_template(template_filename)
        rendered_html = template.render(context)
        print("✓ HTML Rendered successfully")

    except Exception as e:
        print(f"❌ Template Rendering Failed: {e}")
        # Return None or raise logic here depending on preference
        raise RuntimeError(f"Template rendering failed: {e}")

    # 4. Generate PDF with Playwright
    output_pdf = os.path.join(TEMP_DIR, f"{product['id']}_specsheet.pdf")
    
    try:
        async with async_playwright() as p:
            # Launch browser
            # args=['--no-sandbox'] is crucial for running as root/headless on Linux
            browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
            page = await browser.new_page()
            
            # Set content
            await page.set_content(rendered_html, wait_until="networkidle")
            
            # Generate PDF
            # A4 dimensions are roughly 595px x 842px at 72dpi, but Playwright handles 'format="A4"' well
            # print_background=True ensures CSS background colors/images are visible
            await page.pdf(
                path=output_pdf,
                format="A4",
                print_background=True,
                margin={"top": "0px", "right": "0px", "bottom": "0px", "left": "0px"}
            )
            
            await browser.close()
            
        print(f"✅ PDF Generated: {output_pdf}")
        return output_pdf

    except Exception as e:
        print(f"❌ PDF Generation Failed: {e}")
        raise RuntimeError(f"Playwright PDF generation failed: {e}")

# Note: No cleanup of the PDF is done here; the calling function in app.py handles deletion.
