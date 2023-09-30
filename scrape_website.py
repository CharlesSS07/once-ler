#!/usr/bin/env python

import time

import vertexai
from vertexai.language_models import TextEmbeddingModel

vertexai.init(project="stone-botany-397219", location="us-central1")

from typing import List, Optional

# Load the "Vertex AI Embeddings for Text" model
from vertexai.preview.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

# Define an embedding method that uses the model
def encode_texts_to_embeddings(sentences: List[str]) -> List[Optional[List[float]]]:
    try:
        embeddings = model.get_embeddings(sentences)
        return [embedding.values for embedding in embeddings]
    except Exception:
        return [None for _ in range(len(sentences))]

import functools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, List, Tuple

import numpy as np
from tqdm.auto import tqdm

# Generator function to yield batches of sentences
def generate_batches(
    sentences: List[str], batch_size: int
) -> Generator[List[str], None, None]:
    for i in range(0, len(sentences), batch_size):
        yield sentences[i : i + batch_size]


def encode_text_to_embedding_batched(
    sentences: List[str], api_calls_per_second: int = 10, batch_size: int = 5
) -> Tuple[List[bool], np.ndarray]:

    embeddings_list: List[List[float]] = []

    # Prepare the batches using a generator
    batches = generate_batches(sentences, batch_size)

    seconds_per_job = 1 / api_calls_per_second

    with ThreadPoolExecutor() as executor:
        futures = []
        for batch in tqdm(
            batches, total=math.ceil(len(sentences) / batch_size), position=0
        ):
            futures.append(
                executor.submit(functools.partial(encode_texts_to_embeddings), batch)
            )
            time.sleep(seconds_per_job)

        for future in futures:
            embeddings_list.extend(future.result())

    is_successful = [
        embedding is not None for sentence, embedding in zip(sentences, embeddings_list)
    ]
    embeddings_list_successful = np.squeeze(
        np.stack([embedding for embedding in embeddings_list if embedding is not None])
    )
    return is_successful, embeddings_list_successful


if __name__=='__main__':
    
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='Website Vectorizer',
        description='Scrape websites, embed them, and save embeddings to vectordb for querying.')
    
    parser.add_argument('website_domain')
    
    args = parser.parse_args()
    
    BUCKET_URI = f"gs://vectorized_websites/{args.website_domain}"
    
    print(BUCKET_URI)
    
    

