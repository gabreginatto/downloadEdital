# Edital Downloader and Analyzer

This project provides tools for downloading, extracting, and analyzing procurement documents (editais) from various sources.

## Features

- Download procurement documents from various sources
- Extract PDFs from archives
- Analyze PDFs using Google's Gemini models
- Save analysis results

## Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up Google Cloud credentials (if using Vertex AI):

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
```

## Usage

### Download a Procurement Document

```bash
python download_edital.py --url "https://example.com/procurement-document"
```

### Analyze a PDF with Gemini

There are three different scripts for analyzing PDFs with Gemini models, each using a different approach:

#### 1. Using Google Generative AI SDK (Recommended for Development)

This approach uses the Google Generative AI SDK directly, which is simpler and requires only an API key.

```bash
python analyze_pdf_with_gemini_new.py --api-key "YOUR_GOOGLE_AI_API_KEY" --pdf download_test.pdf
```

To get an API key:
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Use the key in the command above

#### 2. Using Vertex AI with PredictionServiceClient

This approach uses the Vertex AI SDK with the PredictionServiceClient, which is more suitable for production environments.

```bash
python analyze_pdf_with_vertex.py --project-id "YOUR_GCP_PROJECT_ID" --pdf download_test.pdf
```

#### 3. Using Vertex AI with GenerativeModel

This approach uses the Vertex AI SDK with the GenerativeModel class from vertexai.preview, which is a newer and more streamlined approach.

```bash
python analyze_pdf_with_vertex_v2.py --project-id "YOUR_GCP_PROJECT_ID" --pdf download_test.pdf
```

### Additional Options

All analysis scripts support the following options:

- `--model-id`: Specify a different Gemini model (default: "gemini-2.0-flash-lite-001")
- `--location`: Specify a different Vertex AI location (default: "us-central1")
- `--pdf-dir`: Specify a different directory containing PDFs (default: "pdfs_simple")

## Output

Analysis results are saved to the `summaries` directory with filenames based on the input PDF.

## Troubleshooting

### Authentication Issues

If you encounter authentication issues with Vertex AI:

1. Ensure you have set up the GOOGLE_APPLICATION_CREDENTIALS environment variable
2. Verify that your service account has the necessary permissions
3. Check that your project has the Vertex AI API enabled

### Model Availability

If you encounter issues with model availability:

1. Verify that the model is available in your region
2. Check that your project has access to the specified model
3. Try using a different model or region

## License

This project is licensed under the MIT License - see the LICENSE file for details. 