from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01"
)

search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

embed_deployment = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")

def get_embedding(text: str) -> list[float]:
    response = openai_client.embeddings.create(
        input=text,
        model=embed_deployment
    )
    return response.data[0].embedding

def index_chunks(chunks: list[str], filename: str):
    documents = []
    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)
        documents.append({
            "id": str(uuid.uuid4()),
            "content": chunk,
            "filename": filename,
            "chunk_index": i,
            "content_vector": embedding
        })

    result = search_client.upload_documents(documents=documents)
    return {"uploaded": len(documents), "success": all(r.succeeded for r in result)}

def search_documents(query: str, top_k: int = 3) -> list[dict]:
    query_embedding = get_embedding(query)

    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k,
        fields="content_vector"
    )

    results = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        select=["content", "filename", "chunk_index"]
    )

    return [
        {
            "content": r["content"],
            "filename": r["filename"],
            "chunk_index": r["chunk_index"],
            "score": r["@search.score"]
        }
        for r in results
    ]

def answer_question(question: str, top_k: int = 4) -> dict:
    retrieved = search_documents(question, top_k)

    context = "\n\n".join(r["content"] for r in retrieved)
    sources = list(set(r["filename"] for r in retrieved))

    system_prompt = (
        "Answer ONLY using the provided context. "
        "If the answer isn't in the context, say so clearly. "
        "Cite which source document supported your answer."
    )

    chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")

    response = openai_client.chat.completions.create(
        model=chat_deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": sources
    }