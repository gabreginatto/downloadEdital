# Edital Downloader

A Python tool for downloading and processing procurement documents (editais) from various Brazilian government procurement portals.

## Features

- Downloads procurement documents from URLs or JSON files with multiple URLs
- Extracts PDFs from archives (ZIP, RAR)
- Organizes PDFs with sequential naming
- Handles different portal formats:
  - PNCP (Portal Nacional de Contratações Públicas)
  - Portal de Compras Públicas
  - AlertaLicitacao URLs

## Installation

1. Clone the repository:
```bash
git clone https://github.com/gabreginatto/downloadEdital.git
cd downloadEdital
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Process a single URL:

```bash
python download_edital.py --url "https://alertalicitacao.com.br/!licitacao/PNCP-XXXXX-X-XXXXX-XXXX"
```

### Process multiple URLs from a JSON file:

```bash
python download_edital.py --json "json/example.json"
```

The JSON file should have the following format:
```json
{
  "licitacoes": [
    {
      "id": "PNCP-XXXXX-X-XXXXX-XXXX",
      "link": "https://alertalicitacao.com.br/!licitacao/PNCP-XXXXX-X-XXXXX-XXXX",
      "objeto": "Description of the procurement"
    },
    ...
  ]
}
```

## Output

The script creates the following directories:
- `downloads_simple/`: Raw downloaded files
- `extracted_simple/`: Extracted content from archives
- `pdfs_simple/`: Final PDFs with sequential naming (example1.pdf, example2.pdf, etc.)

## License

MIT 