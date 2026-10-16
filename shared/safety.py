from azure.ai.contentsafety import ContentSafetyClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.contentsafety.models import AnalyzeTextOptions
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")
key = os.getenv("AZURE_CONTENT_SAFETY_KEY")

client = ContentSafetyClient(endpoint, AzureKeyCredential(key))

def check_text_safety(text: str) -> dict:
    request = AnalyzeTextOptions(text=text[:10000])  # API has a length limit
    response = client.analyze_text(request)

    results = {}
    for category in response.categories_analysis:
        results[category.category] = category.severity

    is_safe = all(severity == 0 for severity in results.values())

    return {
        "is_safe": is_safe,
        "categories": results
    }