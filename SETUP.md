# Setup Instructions

## Quick Setup

Run these commands to get started:

```bash
# Navigate to project directory
cd /Users/williamferns/dev/personal-projects/multi-site-real-estate-scraper

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test the scraper (limit to 1 page for testing)
python runner.py --site property24 --max-pages 1 --verbose
```

## Next Steps

1. **Update CSS Selectors**: The selectors in `config/sites.yaml` are placeholder examples. You'll need to:
   - Visit the actual websites (Property24, Private Property)
   - Inspect the HTML structure
   - Update the CSS selectors to match the real site structure

2. **Test Scraping**: Start with a small test:
   ```bash
   python runner.py --site property24 --max-pages 1 --verbose
   ```

3. **Check Output**: Review the generated files in the `output/` directory

4. **Review Logs**: Check `logs/` for any errors or warnings

## Virtual Environment

A virtual environment has been created at `.venv/`. To use it:

```bash
# Activate
source .venv/bin/activate

# Deactivate when done
deactivate
```

## Installing Dependencies

```bash
# Make sure .venv is activated first
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

## Project Status

✅ All core components created
✅ Configuration files ready
✅ Spiders implemented
✅ Virtual environment initialized

⚠️ **Important**: CSS selectors in `config/sites.yaml` need to be updated to match actual website structure before scraping will work.
