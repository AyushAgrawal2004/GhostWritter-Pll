import os
import tempfile
import subprocess
import gradio as gr

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
            # In Gradio, we can raise an error that shows in the UI
            raise gr.Error("Only .docx files are supported.")
            
        temp_output_path = os.path.join(temp_dir, f"redacted_output.docx")

        # Execute the main.py script
        result = subprocess.run(
            ["python", "main.py", "--mode", "redact", "--input", file_path, "--output", temp_output_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Error running main.py:", result.stderr)
            raise gr.Error("Error during document processing. Check logs.")

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
    title="GhostWriter PII Redaction Engine",
    description="Upload a `.docx` financial document. The local NLP engine will automatically detect and anonymize all PII (Names, Organizations, Addresses, Emails, Phones, URLs) using stateful synthetic surrogates while perfectly preserving table and paragraph formatting.",
    allow_flagging="never"
)

if __name__ == "__main__":
    # Hugging Face Spaces will automatically launch this app on port 7860
    demo.launch(server_name="0.0.0.0", server_port=7860)
