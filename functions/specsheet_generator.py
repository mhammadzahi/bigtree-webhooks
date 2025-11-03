from docxtpl import DocxTemplate
from docx2pdf import convert
import os


def fill_and_convert_template(template_path, output_docx, output_pdf, context_data):
    # Load the template
    doc = DocxTemplate(template_path)
    
    # Fill the template with context data
    doc.render(context_data)

    doc.save(output_docx)
    
    convert(output_docx, output_pdf)
    os.remove(output_docx)


def generate_specsheet_pdf(product):
    template_path = 'files/Bigtree_Specsheet template.docx'
    output_docx = f'temp/{product["id"]}_specsheet.docx'
    output_pdf = f'temp/{product["id"]}_specsheet.pdf'

    context_data = {
        'product_name': product.get('name', 'N/A'),
        'product_sku': product.get('sku', 'N/A'),
        'product_price': product.get('price', 'N/A'),
        'product_description': product.get('description', 'N/A')
    }

    fill_and_convert_template(template_path, output_docx, output_pdf, context_data)
    return output_pdf
