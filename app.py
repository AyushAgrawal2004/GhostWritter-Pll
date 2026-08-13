import os
import tempfile
import subprocess
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title="GhostWriter PII Redaction API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Local PII Redaction Engine"}

@app.post("/api/redact")
async def redact_document(file: UploadFile = File(...)):
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    try:
        # Create a secure temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_input_path = os.path.join(temp_dir, file.filename)
        temp_output_path = os.path.join(temp_dir, f"redacted_{file.filename}")

        # Save the uploaded file
        with open(temp_input_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Execute the main.py script
        result = subprocess.run(
            ["python", "main.py", "--mode", "redact", "--input", temp_input_path, "--output", temp_output_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Error running main.py:", result.stderr)
            raise HTTPException(status_code=500, detail="Error during document processing.")

        if not os.path.exists(temp_output_path):
            raise HTTPException(status_code=500, detail="Processed file was not generated.")

        # Return the processed file
        return FileResponse(
            path=temp_output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"redacted_{file.filename}"
        )

    except Exception as e:
        print(f"Exception during redaction: {str(e)}")
        raise HTTPException(status_code=500, detail="An internal error occurred during processing.")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)
