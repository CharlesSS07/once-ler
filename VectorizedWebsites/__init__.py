
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import pandas as pd
import os
import json
import math
import functools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, List, Tuple
import numpy as np
from tqdm.auto import tqdm

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
vertexai.init(project="stone-botany-397219", location="us-central1")

cache_dir = os.path.join(os.path.split(__file__), 'cache')

def get_website_cache(url:str):
    
    URL = urlparse(url)
    
    website_dir = os.path.join(cache_dir, URL.hostname, URL.path[1:]) # strip leading / off of path
    
    return website_dir

# Define an embedding method that uses the model # stolen from https://colab.research.google.com/github/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/official/matching_engine/sdk_matching_engine_create_stack_overflow_embeddings_vertex.ipynb#scrollTo=9b01baa906b5

# Load the "Vertex AI Embeddings for Text" model
from vertexai.preview.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

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
#    if len(embeddings_list)>0:
#        embeddings_list_successful = np.squeeze(
#            np.stack(embeddings_list)
#        )
#        return is_successful, embeddings_list_successful
    return is_successful, embeddings_list

# Define an embedding method that uses the model
def encode_texts_to_embeddings(sentences: List[str]) -> List[Optional[List[float]]]:
    try:
        embeddings = model.get_embeddings(sentences)
        return [embedding.values for embedding in embeddings]
    except Exception:
        return [None for _ in range(len(sentences))]

#def recursive_split(text, max_length, split_characters, final_split_character):
#
#    text = text.strip()
#    if len(text)<max_length:
#        return text
#
#    if len(split_characters)==0:
#        chunked = text.split(final_split_character)
#        half_split_idx = len(chunked)//2
#        first_half_chunk = final_split_character.join(chunked[:half_split_idx]).strip()
#        second_half_chunk = final_split_character.join(chunked[half_split_idx:]).strip()
#        if len(first_half_chunk)<=max_length:
#            yield first_half_chunk
#            return
#        else:
#            for chunk_i in recursive_split(first_half_chunk, max_length, [], final_split_character):
#                yield chunk_i
#            return
#        if len(second_half_chunk)<=max_length:
#            yield second_half_chunk
#            return
#        else:
#            for chunk_i in recursive_split(second_half_chunk, max_length, [], final_split_character):
#                yield chunk_i
#            return
#
#    for chunk in text.split(split_characters[0]):
#        chunk = chunk.strip()
#        if len(chunk)<=max_length:
#            yield chunk
#        else:
#            for chunk_i in recursive_split(chunk, max_length, split_characters[1:], final_split_character):
#                yield chunk_i

def overlap_split(text, max_chunk_size, chunk_overlap):
    
    l = len(text)
    
    i = max_chunk_size
    yield text[:max_chunk_size]
    
    while True:
        yield text[ i - chunk_overlap : i + max_chunk_size + chunk_overlap ]
        if i + max_chunk_size + chunk_overlap > l:
            break
        i += max_chunk_size

def parse(url:str, page_text: str, page_html: str = None):
    
    website_dir = get_website_cache(url)
    
    if os.path.exists(website_dir):
        # have already scraped this site...
        return # "cached"...
    
    os.makedirs(website_dir)
    
    print('Writing website to:', website_dir)
    
    if page_html is None:
        page_html = requests.get(url).text
    
    with open(os.path.join(website_dir, 'content.html'), 'w') as f:
        f.write(page_html)
    
    with open(os.path.join(website_dir, 'content.txt'), 'w') as f:
        f.write(page_text)
    
    # page_DOM = BeautifulSoup(page_html, features="lxml")
    # parse out links, buttons, etc.
    
    # TODO: make another table of links/buttons in the page, and the href text or surrounding text for the link/button
    # TODO: make a page summary txt (for pages smaller than x) by summarizing overlapping chunks into a running summary
    # TODO: perhaps a second page summary which takes into account all the href text used by links which lead to it
    
    # now, chunk the doc for vectorization
    
    max_chunk_size = 100
    chunks = list(overlap_split(page_text, max_chunk_size, 50))
    
    print(chunks)
    
    embeddings = pd.DataFrame(columns=['embeddings', 'chunks'])
    for i, (c, e) in tqdm(
        enumerate(zip(
            chunks,                         # , task_type='RETRIEVAL_QUERY'
            encode_text_to_embedding_batched([ TextEmbeddingInput(text=c) for c in chunks ])[1]
        )),
        total=len(chunks),
        desc="Chunk --> Embedding",
    ):
        
        # Append to file
        embeddings.loc[i] = {
            "embeddings": e,
            "chunks": c
        }
    
    embeddings.to_pickle(os.path.join(website_dir, 'embeddings.pkl'))

#scrape_website('https://en.wikipedia.org/wiki/Murshidabad')

#parse('https://admissions.utah.edu/information-resources/residency/residency-state-exceptions/', 'XYZ', 'XYZ')
