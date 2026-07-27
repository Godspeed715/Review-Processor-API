"""Review processing helpers using AI APIs for toxicity and similarity checks."""

import os
from asyncio import TaskGroup
from math import sqrt

from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from huggingface_hub import AsyncInferenceClient

from functions.logger import logger

# Load environment variables for the external AI services.
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HF_API_KEY = os.environ.get("HF_API_KEY")


async def merge_sentences(sentences: list) -> str:
    """Use the Gemini API to merge several similar reviews into one sentence."""
    client = genai.Client(api_key=GEMINI_API_KEY).aio
    prompt = "Combine the following similar reviews into a single, concise sentence that captures the core meaning:\n\n"
    for sentence in sentences:
        prompt += f"- {sentence}\n"

    try:
        # Ask Gemini to produce a single merged sentence only.
        interaction = await client.interactions.create(
            model="gemini-3.5-flash",
            system_instruction="You are a helpful assistant. Output ONLY the merged sentence. Do not add conversational filler.",
            input=prompt,
        )
        return interaction.output_text
    except APIError as e:
        logger.warning(f"Gemini API warning in merge_sentences: {e}")
        return sentences[0] if sentences else ""
    except Exception as e:
        logger.error(f"Unexpected error in merge_sentences: {e}", exc_info=True)
        return sentences[0] if sentences else ""


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Calculate the cosine similarity between two vectors."""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = sqrt(sum(a * a for a in vec1))
    norm_b = sqrt(sum(b * b for b in vec2))
    return dot_product / (norm_a * norm_b)


async def check_toxicity(text: str) -> bool:
    """Use the Hugging Face toxicity classifier to flag harmful review text."""
    client = AsyncInferenceClient(api_key=HF_API_KEY)
    try:
        # Send the review text to the remote classification model.
        results = await client.text_classification(text=text, model="unitary/toxic-bert")

        # If the model labels the text as toxic with high confidence, flag it.
        for item in results:
            if item["label"] == "toxic" and item["score"] >= 0.85:
                return True
        return False
    except Exception as e:
        logger.warning(f"Hugging Face Toxicity warning: {e}")
        return False  # Let the review pass if the API fails.


async def get_embedding(text: str) -> list:
    """Return an embedding vector for the given text for similarity comparisons."""
    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        # Request an embedding from Gemini for the review text.
        response = client.models.embed_content(model="gemini-embedding-2", contents=text)
        return response.embeddings[0].values
    except APIError as e:
        logger.warning(f"Embedding API warning: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_embedding: {e}", exc_info=True)
        return []


async def process_reviews(matric_no: str, conn):
    """Fetch reviews, group similar ones, and merge them into concise summaries."""
    try:
        # Use local sample rows until the database-backed version is fully wired up.
        rows = ["Daisy is very nice", "She is so cute", "She is fu**ing everyone", "she is very nice looking", "she is beautiful"]
        if not rows:
            return []

        # Create embeddings for each review in parallel.
        async with TaskGroup() as tg:
            tasks = [tg.create_task(get_embedding(text)) for text in rows]

        vectors = [task.result() for task in tasks]
        sentences_with_vectors = [{"text": text, "vector": vector} for text, vector in zip(rows, vectors)]

        clusters = []
        SIMILARITY_THRESHOLD = 0.70

        # Group reviews that are similar enough to be considered the same idea.
        for item in sentences_with_vectors:
            found_cluster = False
            for cluster in clusters:
                if cosine_similarity(item["vector"], cluster[0]["vector"]) >= SIMILARITY_THRESHOLD:
                    cluster.append(item)
                    found_cluster = True
                    break
            if not found_cluster:
                clusters.append([item])

        final_sentences = []
        # Keep standalone reviews as-is.
        final_sentences.append([cluster[0]["text"] for cluster in clusters if len(cluster) == 1])

        # Merge groups with multiple related reviews into one summary sentence.
        clusters_to_merge = [cluster[0]["text"] for cluster in clusters if len(cluster) >= 2]
        async with TaskGroup() as tg:
            tasks = [tg.create_task(merge_sentences(cluster)) for cluster in clusters_to_merge]

        final_sentences.append([task.result() for task in tasks])
        logger.info(f"Processed reviews for matric_no={matric_no}")
        return final_sentences
    except Exception as e:
        logger.error(f"Error processing reviews for matric_no={matric_no}: {e}", exc_info=True)
        return []