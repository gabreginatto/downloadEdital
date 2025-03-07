#!/usr/bin/env python3
import os
import argparse
import pdfplumber
import traceback
from datetime import datetime
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Part

# Configuration
PDF_DIR = "pdfs_simple"  # Folder containing PDFs
SUMMARY_DIR = "summaries"  # Folder for analysis results

def setup_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs(PDF_DIR, exist_ok=True)
    os.makedirs(SUMMARY_DIR, exist_ok=True)
    print(f"Directories set up: {PDF_DIR}, {SUMMARY_DIR}")

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file using pdfplumber."""
    print(f"Extracting text from {pdf_path}...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for i, page in enumerate(pdf.pages):
                print(f"Processing page {i+1}/{len(pdf.pages)}")
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                else:
                    print(f"Warning: No text extracted from page {i+1}")
        
        if not text.strip():
            print("Warning: No text was extracted from the PDF. It might be a scanned document.")
            return ""
        
        print(f"Successfully extracted {len(text)} characters of text")
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")
        traceback.print_exc()
        return ""

def initialize_vertex_ai(project_id, location):
    """Initialize Vertex AI with the specified project and location."""
    try:
        print(f"Initializing Vertex AI with project: {project_id}, location: {location}")
        aiplatform.init(project=project_id, location=location)
        return True
    except Exception as e:
        print(f"Error initializing Vertex AI: {e}")
        traceback.print_exc()
        return False

def analyze_with_gemini(text, model_id="gemini-2.0-flash-lite-001"):
    """Send text to Gemini model via Vertex AI for analysis."""
    if not text:
        return "No text available for analysis."
    
    try:
        print(f"Analyzing text with Gemini model: {model_id}...")
        
        # Initialize the Gemini model
        model = GenerativeModel(model_id)
        print(f"Model initialized: {model_id}")
        
        # Updated prompt for table extraction with specific guidance about the Termo de Referência
        prompt = """
        Analise este documento de licitação e extraia as seguintes informações, priorizando tabelas e listas que contenham descrições de itens, quantidades e unidades. Formate a resposta de forma clara e organizada, com cada item em uma seção separada. Se alguma informação não estiver disponível no documento, indique "Não especificado".

        IMPORTANTE: Procure especificamente na seção "ANEXO I - TERMO DE REFERÊNCIA" ou "TERMO DE REFERÊNCIA" que geralmente começa após a página 20 do documento. Esta seção contém as tabelas com as especificações detalhadas dos produtos.

        1. Cidade/Município onde será realizada a licitação
        2. Empresa/Órgão responsável pela licitação
        3. Objeto da licitação (o que está sendo licitado)
        4. Especificações técnicas dos produtos/serviços (incluindo detalhes de tabelas como descrições, quantidades, e unidades, organizados por lote se aplicável)
        5. Valores estimados ou de referência (se disponíveis em tabelas ou texto)
        6. Data de abertura da licitação
        7. Prazo para envio de propostas
        8. Requisitos para participação
        9. Critérios de julgamento das propostas

        Para os itens 4 e 5, procure especificamente por tabelas ou listas que detalhem:
        - Descrição do item (e.g., "Tubete Especial Curto Oitavado", "Porca Sextavada")
        - Quantidade (e.g., "2.000", "1.000")
        - Unidade (e.g., "Peça")
        - Organize essas informações em tabelas no formato:
          | ITEM | DESCRIÇÃO                     | QUANTIDADE | UND   |
          |------|-------------------------------|------------|-------|
          | 01   | Tubete Especial Curto Oitavado| 2.000      | Peça  |
          | 02   | Porca Sextavada              | 2.000      | Peça  |
        Se os dados estiverem espalhados ou não em tabelas, compile-os da melhor forma possível em um formato tabular.

        INSTRUÇÕES ESPECÍFICAS:
        1. Para as especificações técnicas (item 4), seja conciso e liste apenas as características principais de cada item, evitando detalhes excessivos.
        2. Para os valores estimados (item 5), além de mostrar os valores por lote, adicione uma linha ao final com o VALOR TOTAL GERAL somando todos os lotes.
        3. Formate a resposta em Markdown para melhor legibilidade.

        Documento:
        """
        
        # Increase the character limit to include more of the document
        max_chars = 50000  # Doubled from previous 25000
        if len(text) > max_chars:
            # Take the first 20000 characters and the last 30000 characters to capture both header info and the Termo de Referência
            first_part = text[:20000]
            last_part = text[-30000:] if len(text) > 30000 else text[20000:]
            text = first_part + "\n...[texto intermediário omitido]...\n" + last_part
        
        # Generate content with increased output tokens
        response = model.generate_content(
            prompt + text,
            generation_config={
                "max_output_tokens": 2048,  # Increased from 1024
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 40
            }
        )
        
        # Extract the response text
        if hasattr(response, 'text'):
            return response.text
        else:
            print("Warning: Unexpected response format")
            return str(response)
            
    except Exception as e:
        print(f"Error analyzing text with Gemini: {e}")
        traceback.print_exc()
        return f"Analysis failed due to an error: {str(e)}"

def save_analysis(analysis, pdf_name):
    """Save the analysis to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(SUMMARY_DIR, f"analysis_{pdf_name.replace('.pdf', '')}.txt")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(analysis)
        print(f"Analysis saved to {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving analysis: {e}")
        traceback.print_exc()
        return None

def process_pdf(pdf_path, project_id, location, model_id):
    """Process a single PDF: extract text and analyze with Gemini."""
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text:
        print(f"No text extracted from {pdf_path}. Skipping analysis.")
        return False
    
    # Analyze with Gemini
    analysis = analyze_with_gemini(text, model_id)
    
    # Save analysis
    pdf_name = os.path.basename(pdf_path)
    save_analysis(analysis, pdf_name)
    
    return True

def main():
    """Main function to analyze a PDF with Gemini."""
    parser = argparse.ArgumentParser(description="Analyze a PDF with Gemini model via Vertex AI.")
    parser.add_argument("--project-id", required=True, help="Google Cloud Project ID")
    parser.add_argument("--location", default="us-central1", help="Vertex AI location")
    parser.add_argument("--model-id", default="gemini-2.0-flash-lite-001", help="Gemini model ID")
    parser.add_argument("--pdf", required=True, help="PDF file to analyze")
    parser.add_argument("--pdf-dir", default=PDF_DIR, help="Directory containing PDFs")
    
    args = parser.parse_args()
    
    # Setup directories
    setup_directories()
    
    # Initialize Vertex AI
    if not initialize_vertex_ai(args.project_id, args.location):
        print("Failed to initialize Vertex AI. Exiting.")
        return
    
    # Get full path to PDF
    pdf_path = args.pdf
    if not os.path.isabs(pdf_path):
        if os.path.exists(pdf_path):
            pdf_path = os.path.abspath(pdf_path)
        elif os.path.exists(os.path.join(args.pdf_dir, args.pdf)):
            pdf_path = os.path.abspath(os.path.join(args.pdf_dir, args.pdf))
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return
    
    # Process the PDF
    success = process_pdf(pdf_path, args.project_id, args.location, args.model_id)
    
    if success:
        print("Analysis complete!")
    else:
        print("Analysis failed.")

if __name__ == "__main__":
    main() 