from docxtpl import DocxTemplate
from docx2pdf import convert
import os


def fill_and_convert_template(template_path, output_docx, output_pdf, context_data):
    doc = DocxTemplate(template_path)
    doc.render(context_data)
    doc.save(output_docx)
    convert(output_docx, output_pdf)
    os.remove(output_docx)


def generate_specsheet_pdf(product):
    template_path = 'files/specsheet_template.docx'
    output_docx = f'files/temp/{product["id"]}_specsheet.docx'
    output_pdf = f'files/temp/{product["id"]}_specsheet.pdf'

    # Helper function to extract meta data by key
    def get_meta_value(meta_data, key):
        for item in meta_data:
            if item.get('key') == key:
                return item.get('value', 'n/a')
        return 'n/a'
    
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
    
    # Build comprehensive context data
    context_data = {
        # Basic Information
        'product_name': product.get('name', 'N/A'),
        'product_sku': product.get('sku', 'N/A'),
        'product_price': product.get('price', 'N/A'),
        'product_description': product.get('description', 'N/A'),
        'short_description': product.get('short_description', 'N/A'),
        
        # Categories and Brand
        'category': categories[0].get('name', 'N/A') if categories else 'N/A',
        'brand': brands[0].get('name', 'N/A') if brands else get_meta_value(meta_data, 'brand'),
        
        # Product Specifications from meta_data
        'type': get_meta_value(meta_data, 'type'),
        'width': get_meta_value(meta_data, 'width'),
        'length': get_meta_value(meta_data, 'length'),
        'size': get_meta_value(meta_data, 'size'),
        'thickness': get_meta_value(meta_data, 'thickness'),
        'weight': get_meta_value(meta_data, 'weight'),
        'composition': get_meta_value(meta_data, 'composition'),
        'pattern': get_meta_value(meta_data, 'pattern'),
        'repeat': get_meta_value(meta_data, 'repeat'),
        'color': get_meta_value(meta_data, 'color'),
        'origin': get_meta_value(meta_data, 'origin'),
        
        # Product Usage
        'application': get_meta_value(meta_data, 'application'),
        'environment': get_meta_value(meta_data, 'environment'),
        'project': get_meta_value(meta_data, 'project'),
        
        # Performance & Durability
        'durability': get_meta_value(meta_data, 'durability'),
        'piling': get_meta_value(meta_data, 'piling'),
        'color_resistance': get_meta_value(meta_data, 'color_resistance'),
        'color_fastness': get_meta_value(meta_data, 'color_fastness'),
        'seam_slippage': get_meta_value(meta_data, 'seam_slippage'),
        'shrinkage_wet': get_meta_value(meta_data, 'shrinkage_wet'),
        
        # Certifications & Compliance
        'flame_retardant': get_meta_value(meta_data, 'flame_retardant'),
        'structural_compliance': get_meta_value(meta_data, 'structural_compliance'),
        'thermal_resistance': get_meta_value(meta_data, 'thermal_resistance'),
        'weather_resistance': get_meta_value(meta_data, 'weather_resistance'),
        'antibacterial': get_meta_value(meta_data, 'antibacterial'),
        'other_certifications': get_meta_value(meta_data, 'other_certifications'),
        
        # Care & Ordering
        'maintenance_care': get_meta_value(meta_data, 'maintenance_&_care'),
        'warranty': get_meta_value(meta_data, 'warranty'),
        'minimum_order_quantity': get_meta_value(meta_data, 'minimum_order_quantity'),
        'lead_time': get_meta_value(meta_data, 'lead_time'),
        'price_tier': get_meta_value(meta_data, 'price_tier'),
        'note': get_meta_value(meta_data, 'note'),
        
        # Attributes (alternative source)
        'product_type_attr': get_attribute_options(attributes, 'Product Type'),
        'color_attr': get_attribute_options(attributes, 'Color'),
        'composition_attr': get_attribute_options(attributes, 'Composition'),
        'application_attr': get_attribute_options(attributes, 'Application'),
        'features': get_attribute_options(attributes, 'Features'),
        
        # Image
        'product_image': images[0].get('src', '') if images else '',
        
        # Additional Info
        'permalink': product.get('permalink', ''),
        'date_created': product.get('date_created', 'N/A'),
    }

    fill_and_convert_template(template_path, output_docx, output_pdf, context_data)
    return output_pdf
