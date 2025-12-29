from docxtpl import DocxTemplate, InlineImage
from docx.shared import Inches, Mm
import subprocess, re, os, requests, platform
from io import BytesIO
from PIL import Image



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
    # Remove excessive newlines (more than 2)
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    
    return clean.strip()


def generate_specsheet_pdf(product):
    template_path = 'files/specsheet_template.docx'
    output_docx = f'files/temp/{product["id"]}_specsheet.docx'
    output_pdf = f'files/temp/{product["id"]}_specsheet.pdf'

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
    
    # Load the template to create InlineImage
    doc = DocxTemplate(template_path)
    
    # Download and prepare image
    image_placeholder = None
    if images and images[0].get('src'):
        try:
            image_url = images[0].get('src')
            # print(f"Downloading image from: {image_url}")
            response = requests.get(image_url, timeout=10, verify=True)
            response.raise_for_status()
            
            # Create InlineImage from downloaded image with height limit
            image_stream = BytesIO(response.content)
            
            # Open image to get dimensions and validate format
            img = Image.open(image_stream)
            img_width, img_height = img.size
            
            # Convert image to RGB if necessary (handles RGBA, P, L, etc.)
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Calculate dimensions to limit height to 300px while maintaining aspect ratio
            max_height_px = 300
            if img_height > max_height_px:
                # Scale down proportionally
                scale_factor = max_height_px / img_height
                new_height_px = max_height_px
            else:
                # Use original size if already smaller than 300px
                new_height_px = img_height
            
            # Convert pixels to inches (96 DPI standard)
            new_height_inches = new_height_px / 96
            
            # Convert image to a format supported by docx (JPEG)
            converted_stream = BytesIO()
            img.save(converted_stream, format='JPEG', quality=95)
            converted_stream.seek(0)
            
            # Create InlineImage with calculated height (using height parameter maintains aspect ratio)
            image_placeholder = InlineImage(doc, converted_stream, height=Inches(new_height_inches))
            # print("Image downloaded and processed successfully")

        except Exception as e:
            print(f"Error processing image (attempt 1): {e}")
            # Try without SSL verification as fallback
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
                
                # Calculate dimensions to limit height to 300px while maintaining aspect ratio
                max_height_px = 300
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
                print("Image processed successfully (without SSL verification)")
            except Exception as e2:
                print(f"Image processing failed completely: {e2}")
                image_placeholder = ""  # Empty string instead of text
    else:
        image_placeholder = ""  # Empty string if no image
    
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
    doc.render(context_data)
    doc.save(output_docx)
    
    # Convert DOCX to PDF using LibreOffice
    # Detect OS and set appropriate LibreOffice path
    system = platform.system()
    
    if system == 'Darwin':  # macOS
        soffice_path = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
    elif system == 'Linux':  # Ubuntu/Linux
        soffice_path = 'libreoffice'
    elif system == 'Windows':
        soffice_path = 'soffice'
    else:
        soffice_path = 'libreoffice'
    
    try:
        subprocess.run([
            soffice_path,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', os.path.dirname(output_pdf),
            output_docx
        ], check=True, capture_output=True)

    except FileNotFoundError:
        raise RuntimeError("LibreOffice is not installed. Please install it: "
                          "macOS: brew install --cask libreoffice | "
                          "Linux: sudo apt-get install libreoffice")
    
    # Clean up the temporary DOCX file
    if os.path.exists(output_docx):
        os.remove(output_docx)
    return output_pdf
