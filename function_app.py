import azure.functions as func
import logging
import os
from shared.extraction import extract_text
from shared.safety import check_text_safety
from shared.chunking import chunk_text
from shared.rag import index_chunks
from shared.db import get_db, save_upload_history

app = func.FunctionApp()

@app.function_name(name="ProcessDocument")
@app.blob_trigger(arg_name="myblob", path="uploaded-documents/{name}", connection="AZURE_STORAGE_CONNECTION_STRING")
def process_document(myblob: func.InputStream):
    filename = myblob.name.split('/')[-1]
    logging.info(f"Started processing: {filename}")

    temp_path = f"/tmp/{filename}"
    os.makedirs("/tmp", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(myblob.read())

    try:
        extracted_text = extract_text(temp_path)
        safety_result = check_text_safety(extracted_text)

        if not safety_result["is_safe"]:
            logging.warning(f"{filename} failed safety check: {safety_result['categories']}")
            return

        chunks = chunk_text(extracted_text)
        index_result = index_chunks(chunks, filename)

        db = next(get_db())
        try:
            save_upload_history(
                db=db,
                filename=filename,
                is_safe=safety_result["is_safe"],
                hate_score=safety_result["categories"].get("Hate", 0),
                violence_score=safety_result["categories"].get("Violence", 0),
                self_harm_score=safety_result["categories"].get("SelfHarm", 0),
            )
        finally:
            db.close()

        logging.info(f"Completed: {filename} — {len(chunks)} chunks indexed")
    except Exception as e:
        logging.error(f"Failed processing {filename}: {str(e)}")
        raise
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)