from docxtpl import DocxTemplate, InlineImage, RichText
from docx.shared import Inches, Mm
import subprocess, re, os, requests, platform
from io import BytesIO
from PIL import Image
from woocommerce import API



def strip_html_tags(text):
    """Remove HTML tags from text and clean up formatting"""
    if not text:
        return ''
    # Remove HTML tags but preserve line breaks
    clean = re.sub(r'<br\s*/?>', '\n', text)  # Convert <br> to newlines
    clean = re.sub(r'</p>\s*<p>', '\n\n', clean)  # Convert paragraph breaks to double newlines
    clean = re.sub(r'<[^>]+>', '', clean)  # Remove all other HTML tags
    # Replace HTML entities
    clean = clean.replace('&nbsp;', ' ')
    clean = clean.replace('&amp;', '&')
    clean = clean.replace('&lt;', '<')
    clean = clean.replace('&gt;', '>')
    # Clean up \r\n to just \n
    clean = clean.replace('\\r\\n', '\n')
    clean = clean.replace('\r\n', '\n')
    clean = clean.replace('\\n', '\n')
    # Clean up multiple spaces but preserve newlines
    clean = re.sub(r' +', ' ', clean)
    # Remove excessive newlines (more than 2 consecutive newlines)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    # Remove trailing newlines at the end of each line
    clean = re.sub(r'\n\s*\n', '\n\n', clean)
    # Remove leading/trailing whitespace on each line
    lines = clean.split('\n')
    lines = [line.strip() for line in lines]
    # Remove empty lines at the start and end, keep max 1 blank line between content
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if not line:
            if not prev_empty and cleaned_lines:  # Allow one blank line
                cleaned_lines.append(line)
            prev_empty = True
        else:
            cleaned_lines.append(line)
            prev_empty = False
    
    # Join and strip final result
    return '\n'.join(cleaned_lines).strip()


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

def get_root_parent_category(category_id):
    """
    Recursively find the root parent category by querying the WooCommerce API.
    Returns the root category object.
    """
    global wcapi
    
    if wcapi is None:
        print("  ⚠️ WooCommerce API not initialized, cannot fetch parent category")
        return None
    
    try:
        # Get category details from API
        response = wcapi.get(f"products/categories/{category_id}")
        
        if response.status_code != 200:
            print(f"  ❌ API error fetching category {category_id}: {response.status_code}")
            return None
            
        category = response.json()
        parent_id = category.get('parent', 0)
        
        # If no parent, this IS the root category
        if parent_id == 0:
            print(f"  ✓ Found root category: {category.get('name')} (ID: {category_id})")
            return category
        
        # Otherwise, recursively check the parent
        print(f"  → Category '{category.get('name')}' has parent ID {parent_id}, checking parent...")
        return get_root_parent_category(parent_id)
        
    except Exception as e:
        print(f"  ❌ Error fetching category {category_id}: {e}")
        return None


def get_template_by_category(product, wc_url=None, wc_key=None, wc_secret=None):
    """
    Determine which template to use based on product category.
    Traverses the category hierarchy to find the root parent category.
    Returns the template file path.
    """
    # Initialize WooCommerce API if credentials provided
    if wc_url and wc_key and wc_secret:
        init_woocommerce_api(wc_url, wc_key, wc_secret)
    
    print("\n=== TEMPLATE SELECTION DEBUG ===")
    print(f"Product ID: {product.get('id', 'N/A')}")
    print(f"Product Name: {product.get('name', 'N/A')}")
    
    categories = product.get('categories', [])
    print(f"Categories found: {len(categories)}")
    
    if not categories:
        print("⚠️ No categories found - using ALL template")
        return 'files/specsheet-template__ALL.docx'
    
    # Display all categories
    categories_info = [(cat.get('name'), cat.get('id')) for cat in categories]
    print(f"All categories: {categories_info}")
    
    # Map of known parent category names to template files
    known_parent_categories = {
        'fabric': 'files/specsheet-template__FABRIC.docx',
        'leather': 'files/specsheet-template__LEATHER.docx',
        'floor covering': 'files/specsheet-template__FLOOR_COVERING.docx',
        'wallcovering': 'files/specsheet-template__WALL_COVERING.docx',
        'wall covering': 'files/specsheet-template__WALL_COVERING.docx',
        'fine art': 'files/specsheet-template__FINE_ART.docx',
        'lighting': 'files/specsheet-template__LIGHTING.docx',
        'objects': 'files/specsheet-template__OBJECTS.docx',
        'furniture': None,  # Special handling below
    }
    
    # Use API to find the root parent category
    print("\nFinding root parent category via API...")
    first_category_id = categories[0].get('id')
    print(f"Starting with category ID: {first_category_id} ({categories[0].get('name')})")
    
    root_category = get_root_parent_category(first_category_id)
    
    if not root_category:
        print("⚠️ Could not determine root category via API - using ALL template")
        return 'files/specsheet-template__ALL.docx'
    
    root_name = root_category.get('name', '').lower()
    print(f"\n✓ Root parent category: {root_category.get('name')}")
    
    # Check for Furniture (needs special subcategory handling)
    if root_name == 'furniture':
        print("✓ Furniture category detected, checking subcategories...")
        # Check all product categories for seating-related ones
        for cat in categories:
            cat_name = cat.get('name', '').lower()
            cat_slug = cat.get('slug', '').lower()
            if any(keyword in cat_name or keyword in cat_slug for keyword in ['seating', 'chair', 'sofa']):
                print(f"  ✓ Found seating subcategory: {cat.get('name')}")
                print("✓ Using FURNITURE_SEATING template")
                return 'files/specsheet-template__FURNITURE_SEATING.docx'
        print("✓ Using FURNITURE_OTHERS template")
        return 'files/specsheet-template__FURNITURE_OTHERS.docx'
    
    # Check if root category matches known categories
    if root_name in known_parent_categories and known_parent_categories[root_name]:
        template = known_parent_categories[root_name]
        print(f"✓ Match found! {root_category.get('name')} → {template}")
        return template
    
    # Default template if no match found
    print("⚠️ No matching template found - using ALL template")
    return 'files/specsheet-template__ALL.docx'


def generate_specsheet_pdf(product, wc_url=None, wc_key=None, wc_secret=None):
    print("\n" + "="*50)
    print("STARTING SPECSHEET PDF GENERATION")
    print("="*50)
    
    # Select template based on product category
    template_path = get_template_by_category(product, wc_url, wc_key, wc_secret)
    output_docx = f'files/temp/{product["id"]}_specsheet.docx'
    output_pdf = f'files/temp/{product["id"]}_specsheet.pdf'
    
    print(f"\nSelected template: {template_path}")
    print(f"Output DOCX: {output_docx}")
    print(f"Output PDF: {output_pdf}")

    # Helper function to extract meta data by key
    def get_meta_value(meta_data, key, clean_html=False):
        for item in meta_data:
            if item.get('key') == key:
                value = item.get('value', '')
                # Return the value as-is, even if it's "n/a"
                result = value if value else 'N/A'
                # Clean HTML if requested
                if clean_html and result != 'N/A':
                    result = strip_html_tags(result)
                return result
        return 'N/A'
    
    # Helper function to extract attribute options
    def get_attribute_options(attributes, attr_name):
        for attr in attributes:
            if attr.get('name') == attr_name or attr.get('slug') == attr_name:
                options = attr.get('options', [])
                return ', '.join(options) if options else 'n/a'
        return 'n/a'

    # Extract meta data
    meta_data = product.get('meta_data', [])
    attributes = product.get('attributes', [])
    categories = product.get('categories', [])
    brands = product.get('brands', [])
    images = product.get('images', [])
    
    print(f"\n=== PRODUCT DATA EXTRACTION ===")
    print(f"Meta data items: {len(meta_data)}")
    print(f"Attributes: {len(attributes)}")
    print(f"Categories: {len(categories)}")
    print(f"Brands: {len(brands)}")
    print(f"Images: {len(images)}")
    
    # Load the template to create InlineImage
    print(f"\nLoading template: {template_path}")
    doc = DocxTemplate(template_path)
    print("✓ Template loaded successfully")
    
    # Download and prepare image
    print(f"\n=== IMAGE PROCESSING ===")
    image_placeholder = None
    if images and images[0].get('src'):
        try:
            image_url = images[0].get('src')
            print(f"Downloading image from: {image_url}")
            response = requests.get(image_url, timeout=10, verify=True)
            response.raise_for_status()
            
            # Create InlineImage from downloaded image with height limit
            image_stream = BytesIO(response.content)
            
            # Open image to get dimensions and validate format
            img = Image.open(image_stream)
            img_width, img_height = img.size
            print(f"Image dimensions: {img_width}x{img_height} pixels")
            print(f"Image mode: {img.mode}")
            
            # Convert image to RGB if necessary (handles RGBA, P, L, etc.)
            if img.mode not in ('RGB', 'L'):
                print(f"Converting image from {img.mode} to RGB")
                img = img.convert('RGB')
            
            # Calculate dimensions to limit height to 300px while maintaining aspect ratio
            max_height_px = 342.42519685
            if img_height > max_height_px:
                # Scale down proportionally
                scale_factor = max_height_px / img_height
                new_height_px = max_height_px
                print(f"Scaling image down: {img_height}px → {new_height_px}px (scale: {scale_factor:.2f})")
            else:
                # Use original size if already smaller than 300px
                new_height_px = img_height
                print(f"Image size OK: {img_height}px (no scaling needed)")
            
            # Convert pixels to inches (96 DPI standard)
            new_height_inches = new_height_px / 96
            print(f"Final image height: {new_height_inches:.2f} inches")
            
            # Convert image to a format supported by docx (JPEG)
            converted_stream = BytesIO()
            img.save(converted_stream, format='JPEG', quality=95)
            converted_stream.seek(0)
            
            # Create InlineImage with calculated height (using height parameter maintains aspect ratio)
            image_placeholder = InlineImage(doc, converted_stream, height=Inches(new_height_inches))
            print("✓ Image downloaded and processed successfully")

        except Exception as e:
            print(f"❌ Error processing image (attempt 1): {e}")
            # Try without SSL verification as fallback
            print("Retrying without SSL verification...")
            try:
                response = requests.get(image_url, timeout=10, verify=False)
                response.raise_for_status()
                image_stream = BytesIO(response.content)
                
                # Open image to get dimensions and validate format
                img = Image.open(image_stream)
                img_width, img_height = img.size
                
                # Convert image to RGB if necessary
                if img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Calculate dimensions to limit height to 342.42519685px while maintaining aspect ratio
                max_height_px = 342.42519685
                if img_height > max_height_px:
                    new_height_px = max_height_px
                else:
                    new_height_px = img_height
                
                # Convert pixels to inches
                new_height_inches = new_height_px / 96
                
                # Convert image to JPEG format
                converted_stream = BytesIO()
                img.save(converted_stream, format='JPEG', quality=95)
                converted_stream.seek(0)
                
                image_placeholder = InlineImage(doc, converted_stream, height=Inches(new_height_inches))
                print("✓ Image processed successfully (without SSL verification)")
            except Exception as e2:
                print(f"❌ Image processing failed completely: {e2}")
                image_placeholder = ""  # Empty string instead of text
    else:
        print("⚠️ No images found for product")
        image_placeholder = ""  # Empty string if no image
    
    # Build REQUEST_INQUIRY URL as clickable hyperlink
    print(f"\n=== REQUEST_INQUIRY URL GENERATION ===")
    product_slug = product.get('slug', '')
    print(f"Product slug: {product_slug}")
    print(f"WC Store URL: {wc_url}")
    
    if wc_url and product_slug:
        # Remove trailing slash from wc_url if present
        base_url = wc_url.rstrip('/')
        request_inquiry_url = f"{base_url}/product/{product_slug}/"
        # Create clickable hyperlink using RichText with "REQUEST INQUIRY" as display text
        request_inquiry_link = RichText('REQUEST INQUIRY', url_id=doc.build_url_id(request_inquiry_url), color='0563C1', underline=True)
        print(f"✓ REQUEST_INQUIRY link created: 'REQUEST INQUIRY' → {request_inquiry_url}")
        print(f"✓ RichText object type: {type(request_inquiry_link)}")
        print(f"⚠️ IMPORTANT: Template must use {{{{ r REQUEST_INQUIRY }}}} or {{% r 'REQUEST_INQUIRY' %}} syntax for RichText!")
    else:
        request_inquiry_link = 'REQUEST INQUIRY'
        print(f"⚠️ REQUEST_INQUIRY created without link - missing slug or wc_url")
    
    # Build comprehensive context data
    context_data = {
        # Basic Information (matching template placeholders)
        'prdct_name': product.get('name', 'N/A'),
        'product_name': product.get('name', 'N/A'),
        'product_sku': product.get('sku', 'N/A'),
        'product_price': product.get('price', 'N/A'),
        'prdct_description': strip_html_tags(product.get('description', 'N/A')),
        'product_description': strip_html_tags(product.get('description', 'N/A')),
        'short_description': strip_html_tags(product.get('short_description', 'N/A')),
        
        # REQUEST_INQUIRY URL (clickable hyperlink)
        'REQUEST_INQUIRY': request_inquiry_link,
        
        # Categories and Brand (matching template placeholders)
        'prdct_category': categories[0].get('name', 'N/A') if categories else 'N/A',
        'category': categories[0].get('name', 'N/A') if categories else 'N/A',
        'brand': brands[0].get('name', 'N/A') if brands else get_meta_value(meta_data, 'brand'),
        
        # Product Specifications from meta_data - DETAIL section
        'type': get_meta_value(meta_data, 'type'),
        'width': get_meta_value(meta_data, 'width'),
        'length': get_meta_value(meta_data, 'length'),
        'size': get_meta_value(meta_data, 'size'),
        'thickness': get_meta_value(meta_data, 'thickness'),
        'weight': get_meta_value(meta_data, 'weight'),
        'composition': get_meta_value(meta_data, 'composition'),
        'backing': get_meta_value(meta_data, 'backing'),
        'pattern': get_meta_value(meta_data, 'pattern'),
        'repeat': get_meta_value(meta_data, 'repeat'),
        'color': get_meta_value(meta_data, 'color'),
        'origin': get_meta_value(meta_data, 'origin'),
        
        # Product Usage - PRODUCT USAGE section
        'application': get_meta_value(meta_data, 'application'),
        'environment': get_meta_value(meta_data, 'environment'),
        'project': get_meta_value(meta_data, 'project', clean_html=True),
        
        # Performance & Durability - TECHNICAL DATA section
        'durability': get_meta_value(meta_data, 'durability'),
        'piling': get_meta_value(meta_data, 'piling'),
        'color_resistance': get_meta_value(meta_data, 'color_resistance'),
        'color_fastness': get_meta_value(meta_data, 'color_fastness', clean_html=True),
        'seam_slippage': get_meta_value(meta_data, 'seam_slippage'),
        'shrinkage_wet': get_meta_value(meta_data, 'shrinkage_wet'),
        
        # Certifications & Compliance
        'flame_retardant': get_meta_value(meta_data, 'flame_retardant', clean_html=True),
        'structural_compliance': get_meta_value(meta_data, 'structural_compliance'),
        'thermal_resistance': get_meta_value(meta_data, 'thermal_resistance'),
        'weather_resistance': get_meta_value(meta_data, 'weather_resistance'),
        'antibacterial': get_meta_value(meta_data, 'antibacterial'),
        'other_certifications': get_meta_value(meta_data, 'other_certifications'),
        
        # Care & Ordering - MAINTENANCE & CARE and KEY FACTS sections
        'maintenance_care': get_meta_value(meta_data, 'maintenance_&_care', clean_html=True),
        'warranty': get_meta_value(meta_data, 'warranty'),
        'minimum_order_quantity': get_meta_value(meta_data, 'minimum_order_quantity'),
        'lead_time': get_meta_value(meta_data, 'lead_time'),
        'price_tier': get_meta_value(meta_data, 'price_tier'),
        'note': get_meta_value(meta_data, 'note'),
        
        # Image
        'product_image': images[0].get('src', '') if images else '',
        'image_placeholder': image_placeholder,
        
        # Additional Info
        'permalink': product.get('permalink', ''),
        'date_created': product.get('date_created', 'N/A'),
    }

    # Render and save the document
    print(f"\n=== DOCUMENT RENDERING ===")
    print("Rendering template with context data...")
    doc.render(context_data)
    print(f"Saving DOCX to: {output_docx}")
    doc.save(output_docx)
    print("✓ DOCX file saved successfully")
    
    # Convert DOCX to PDF using LibreOffice
    print(f"\n=== PDF CONVERSION ===")
    # Detect OS and set appropriate LibreOffice path
    system = platform.system()
    print(f"Detected OS: {system}")
    
    if system == 'Darwin':  # macOS
        soffice_path = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    elif system == 'Linux':  # Ubuntu/Linux
        soffice_path = 'libreoffice'
    elif system == 'Windows':
        soffice_path = 'soffice'
    else:
        soffice_path = 'libreoffice'
    
    print(f"LibreOffice path: {soffice_path}")
    print("Converting DOCX to PDF...")
    
    try:
        result = subprocess.run([
            soffice_path,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(output_pdf),
            output_docx
        ], check=True, capture_output=True)
        
        print("✓ PDF conversion successful")
        if result.stdout:
            print(f"LibreOffice output: {result.stdout.decode()}")

    except FileNotFoundError:
        print("❌ LibreOffice not found")
        raise RuntimeError("LibreOffice is not installed. Please install it: "
                          "macOS: brew install --cask libreoffice | "
                          "Linux: sudo apt-get install libreoffice")
    except subprocess.CalledProcessError as e:
        print(f"❌ PDF conversion failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr.decode()}")
        raise
    
    # Clean up the temporary DOCX file
    print(f"\n=== CLEANUP ===")
    if os.path.exists(output_docx):
        print(f"Removing temporary DOCX: {output_docx}")
        os.remove(output_docx)
        print("✓ Cleanup complete")
    
    print(f"\n✅ PDF generated successfully: {output_pdf}")
    print("="*50 + "\n")
    return output_pdf
