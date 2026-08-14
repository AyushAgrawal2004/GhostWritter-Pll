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

custom_css = """
body {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}
.gradio-container {
    max-width: 900px !important;
    margin: 0 auto;
    padding-top: 40px;
}
h1 {
    text-align: center;
    color: #38bdf8;
    font-weight: 800;
    margin-bottom: 5px;
}
.warning-box {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid #ef4444;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 25px;
    color: #fca5a5;
    text-align: center;
    font-size: 0.95em;
    backdrop-filter: blur(10px);
}
.warning-box a {
    color: #60a5fa;
    text-decoration: underline;
    font-weight: bold;
}
.upload-box, .download-box {
    border-radius: 16px;
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid #334155;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
}
"""

@spaces.GPU(duration=50)
def redact_document(input_file):
    if input_file is None:
        return None
        
    try:
        temp_dir = tempfile.mkdtemp()
        
        if hasattr(input_file, "name"):
            file_path = input_file.name
        else:
            file_path = input_file
            
        # File Size Limit Check (500 KB limit for HF Spaces ZeroGPU 50s constraint)
        file_size_bytes = os.path.getsize(file_path)
        if file_size_bytes > 500 * 1024:
            raise gr.Error("File is too large for the free ZeroGPU tier. Please upload a file smaller than 500 KB, or run locally for massive documents.")

        original_filename = os.path.basename(file_path)
        if not original_filename.endswith('.docx'):
            raise gr.Error("Only .docx files are supported.")
            
        temp_output_path = os.path.join(temp_dir, f"redacted_output.docx")

        print("Initializing NLP Models on ZeroGPU...")
        detector = HybridDetector(whitelist=WHITELIST)
        mapper = StatefulMapper()
        handler = DocxHandler(detector=detector, mapper=mapper)
        
        print("Starting document redaction...")
        handler.process_document(file_path, temp_output_path)
        print("Redaction complete.")

        if not os.path.exists(temp_output_path):
            raise gr.Error("Processed file was not generated.")

        return temp_output_path

    except Exception as e:
        print(f"Exception during redaction: {str(e)}")
        raise gr.Error(f"An internal error occurred: {str(e)}")

with gr.Blocks(css=custom_css, theme=gr.themes.Base()) as demo:
    gr.Markdown("# 🛡️ GhostWriter PII Redaction Engine")
    
    gr.HTML('''
    <div class="warning-box">
        ⚠️ <strong>Notice:</strong> This model is currently deployed on a free Hugging Face ZeroGPU server, limited to 50 seconds of processing time (Max file size: 500 KB).<br/>
        To unlock the full potential of this engine on unlimited document sizes, please run it locally from the GitHub repository: 
        <a href="https://github.com/AyushAgrawal2004/GhostWritter-Pll" target="_blank">AyushAgrawal2004/GhostWritter-Pll</a>
    </div>
    ''')
    
    with gr.Row():
        with gr.Column():
            input_doc = gr.File(label="Upload Original DOCX", elem_classes="upload-box")
            submit_btn = gr.Button("Anonymize Document 🚀", variant="primary")
        with gr.Column():
            output_doc = gr.File(label="Download Redacted DOCX", elem_classes="download-box")
            
    submit_btn.click(fn=redact_document, inputs=input_doc, outputs=output_doc)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
