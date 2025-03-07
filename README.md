# Edital Downloader

A Python script for automatically downloading procurement documents ("editais") from various Brazilian government portals.

## Features

- Downloads procurement files from URLs in a JSON file
- Extracts PDFs from archives (ZIP, RAR)
- Organizes PDFs in a dedicated directory with sequential naming
- Handles dynamic websites that require button clicks using Playwright
- Cookie consent handling for websites with overlays

## Requirements

- Python 3.6+
- Playwright for automated browsing
- Beautiful Soup for HTML parsing
- Requests for HTTP requests
- unar for archive extraction

## Installation

1. Clone the repository:
```bash
git clone https://github.com/gabreginatto/downloadEdital.git
cd downloadEdital
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browser:
```bash
python -m playwright install chromium
```

4. Make sure unar is installed:
```bash
# On macOS
brew install unar

# On Ubuntu/Debian
sudo apt-get install unar
```

## Usage

### Basic Usage

```bash
python download_edital.py --json path/to/urls.json
```

### Example JSON Input Format

```json
{
  "licitacoes": [
    {
      "id": "PNCP-86050978000183-1-000145-2024",
      "titulo": "Edital PCE 81/2024",
      "orgao": "SERVICO AUTONOMO MUNICIPAL DE AGUA E ESGOTO",
      "objeto": "Aquisição de hidrômetros",
      "abertura": "05/11/2024",
      "link": "https://alertalicitacao.com.br/!licitacao/PNCP-86050978000183-1-000145-2024"
    }
  ]
}
```

### Testing

Run the enhanced test script to verify the functionality:

```bash
python test_enhanced.py
```

## How It Works

1. The script reads URLs from a JSON file
2. For each URL:
   - Detects if it's a dynamic page that might require Playwright
   - Handles cookie consent dialogs
   - Downloads the file using requests or Playwright
   - Extracts archives if needed
   - Organizes PDFs in a sequential manner

## License

MIT 