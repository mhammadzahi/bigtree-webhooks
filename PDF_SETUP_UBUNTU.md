# PDF Generation Setup for Ubuntu Production Server

## Problem
LibreOffice's direct `soffice --convert-to pdf` command often produces poor quality PDFs with formatting issues.

## Solution: Install unoconv (RECOMMENDED)

### What is unoconv?
`unoconv` is a better interface to LibreOffice that produces higher quality PDFs with better formatting preservation.

### Installation on Ubuntu

```bash
# Update package list
sudo apt-get update

# Install unoconv and LibreOffice Writer
sudo apt-get install -y unoconv libreoffice-writer libreoffice-core

# Verify installation
unoconv --version
```

### Alternative: Improve LibreOffice Only

If you can't install unoconv, ensure LibreOffice is properly installed:

```bash
sudo apt-get install -y libreoffice-writer libreoffice-core
```

The code will automatically fall back to LibreOffice with optimized settings.

## Testing

After installation, test PDF generation:

```bash
# Test unoconv
unoconv -f pdf test.docx

# Test LibreOffice
soffice --headless --convert-to pdf test.docx
```

## Priority Order

The code uses this priority:
1. **macOS/Windows**: docx2pdf (uses MS Word) → unoconv → LibreOffice
2. **Linux/Ubuntu**: unoconv → LibreOffice with optimized settings

## Performance Notes

- **unoconv**: ~3-5 seconds per document, best quality
- **LibreOffice direct**: ~2-4 seconds per document, acceptable quality
- Both methods work in background tasks without blocking

## Troubleshooting

### "unoconv: Cannot find a suitable office installation"

```bash
# Set LibreOffice path explicitly
export UNO_PATH=/usr/lib/libreoffice/program

# Or reinstall
sudo apt-get remove --purge unoconv libreoffice-*
sudo apt-get install -y unoconv libreoffice-writer
```

### LibreOffice hanging or timing out

```bash
# Kill existing LibreOffice processes
pkill -9 soffice

# Remove lock files
rm -rf ~/.config/libreoffice

# Restart the conversion
```

### Low quality PDFs

- Ensure your DOCX templates use standard fonts (Arial, Times New Roman, Calibri)
- Avoid complex nested tables
- Use standard Word styles instead of manual formatting
- Images should be high resolution (300+ DPI)
- Test template directly in LibreOffice: File → Export as PDF

## Deployment Checklist

- [ ] Install unoconv: `sudo apt-get install -y unoconv libreoffice-writer`
- [ ] Test conversion: `unoconv --version`
- [ ] Verify fonts are available: `fc-list | grep -i arial`
- [ ] Test your actual templates with sample data
- [ ] Monitor conversion times in production logs
