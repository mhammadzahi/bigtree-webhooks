# PDF Generation Setup for Ubuntu Production Server

## Current Status ✅

**LibreOffice is working** - The system successfully generates PDFs using LibreOffice's direct conversion.

## Why PDFs Look "Ugly"

The issue is **NOT** the conversion tool - it's the **DOCX template formatting**. LibreOffice's PDF engine cannot perfectly replicate Microsoft Word's complex formatting, especially:

- Complex nested tables
- Custom fonts not available on Ubuntu
- Advanced Word styles and effects
- Precise spacing and alignment

## BEST SOLUTION: Optimize Your DOCX Templates

### 1. Simplify Template Formatting

Open your DOCX templates in LibreOffice Writer on your local machine and:

- **Remove complex tables** - Use simple tables without merged cells
- **Use standard fonts** - Arial, Times New Roman, Liberation Sans/Serif
- **Remove Word-specific features** - SmartArt, WordArt, special effects
- **Test locally** - File → Export as PDF in LibreOffice to preview

### 2. Install Fonts on Ubuntu (Critical)

```bash
# Install Microsoft-compatible fonts
sudo apt-get install -y ttf-mscorefonts-installer fonts-liberation fonts-liberation2

# Update font cache
sudo fc-cache -f -v

# Verify fonts
fc-list | grep -i "arial\|times\|calibri"
```

### 3. Current Setup (Already Working)

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
