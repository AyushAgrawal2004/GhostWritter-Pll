import os
import tempfile
import gradio as gr
import spaces

from src.detectors.hybrid_detector import HybridDetector
from src.redactors.mapper import StatefulMapper
from src.redactors.docx_handler import DocxHandler

WHITELIST = [
    "Cap Price", "Floor Price", "Offer Price", "Book Building Process", 
    "Cut-off Price", "Red Herring Prospectus", "Equity Shares", 
    "Offer for Sale", "Fresh Issue", "SEBI", "BSE", "NSE", "Companies Act",
    "Selling Shareholder", "Selling Shareholders", "Promoter Selling Shareholder", 
    "Company Secretary", "Compliance Officer", "Book Running Lead Manager", 
    "Statutory Auditors", "Chartered Accountants",
    "REGISTERED OFFICE", "CORPORATE OFFICE", "CONTACT PERSON", 
    "E-MAIL AND TELEPHONE", "WEBSITE", "DETAILS OF THE OFFER TO PUBLIC", 
    "TYPE", "SIZE OF THE FRESH ISSUE", "TOTAL OFFER SIZE", 
    "ELIGIBILITY AND SHARE RESERVATION", "Qualified Institutional Buyers", 
    "Retail Individual Investors", "Stock Exchanges", "BSE Limited", 
    "National Stock Exchange of India Limited", "ISSUER'S"
]

@spaces.GPU(duration=50)
def redact_document(input_file):
    if input_file is None:
        return None
        
    try:
        # Create a secure temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # input_file in gradio is a temporary file path when using type="filepath" (default for gr.File)
        # or an object with a .name attribute. Let's ensure we get the path.
        if hasattr(input_file, "name"):
            file_path = input_file.name
        else:
            file_path = input_file
            
        original_filename = os.path.basename(file_path)
        if not original_filename.endswith('.docx'):
            raise gr.Error("Only .docx files are supported.")
            
        temp_output_path = os.path.join(temp_dir, f"redacted_output.docx")

        # Initialize detector, mapper, and handler INSIDE the GPU context
        # so that GLiNER loads the model onto the dynamically assigned GPU
        print("Initializing NLP Models on ZeroGPU...")
        detector = HybridDetector(whitelist=WHITELIST)
        mapper = StatefulMapper()
        handler = DocxHandler(detector=detector, mapper=mapper)
        
        # Process the document
        print("Starting document redaction...")
        handler.process_document(file_path, temp_output_path)
        print("Redaction complete.")

        if not os.path.exists(temp_output_path):
            raise gr.Error("Processed file was not generated.")

        # Return the path to the processed file so Gradio can offer it for download
        return temp_output_path

    except Exception as e:
        print(f"Exception during redaction: {str(e)}")
        raise gr.Error(f"An internal error occurred: {str(e)}")

# Define the Gradio Interface
demo = gr.Interface(
    fn=redact_document,
    inputs=gr.File(label="Upload Original DOCX (Red Herring Prospectus)"),
    outputs=gr.File(label="Download Redacted DOCX"),
    title="GhostWriter PII Redaction Engine (ZeroGPU Accelerated)",
    description="Upload a `.docx` financial document. The local NLP engine will automatically detect and anonymize all PII using stateful synthetic surrogates while perfectly preserving table and paragraph formatting. Accelerated by Hugging Face ZeroGPU."
)

if __name__ == "__main__":
    # Hugging Face Spaces will automatically launch this app on port 7860
    demo.launch(server_name="0.0.0.0", server_port=7860)
