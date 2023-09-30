
import requests
from urllib.parse import urlparse
from readability import Document
from bs4 import BeautifulSoup
import os
import gc
import json
import math

data_dir, _ = os.path.split(__file__)

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput

vertexai.init(project="stone-botany-397219", location="us-central1")

# Define an embedding method that uses the model # stolen from https://colab.research.google.com/github/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/official/matching_engine/sdk_matching_engine_create_stack_overflow_embeddings_vertex.ipynb#scrollTo=9b01baa906b5
from typing import List, Optional

# Load the "Vertex AI Embeddings for Text" model
from vertexai.preview.language_models import TextEmbeddingModel

from typing import List, Optional

# Load the "Vertex AI Embeddings for Text" model
from vertexai.preview.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

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

import numpy as np
from tqdm.auto import tqdm

def recursive_split(text, max_length, split_characters, final_split_character):
    
    text = text.strip()
    if len(text)<max_length:
        return text

    if len(split_characters)==0:
        chunked = text.split(final_split_character)
        half_split_idx = len(chunked)//2
        first_half_chunk = final_split_character.join(chunked[:half_split_idx]).strip()
        second_half_chunk = final_split_character.join(chunked[half_split_idx:]).strip()
        if len(first_half_chunk)<=max_length:
            yield first_half_chunk
            return
        else:
            for chunk_i in recursive_split(first_half_chunk, max_length, [], final_split_character):
                yield chunk_i
            return
        if len(second_half_chunk)<=max_length:
            yield second_half_chunk
            return
        else:
            for chunk_i in recursive_split(second_half_chunk, max_length, [], final_split_character):
                yield chunk_i
            return
    
    for chunk in text.split(split_characters[0]):
        chunk = chunk.strip()
        if len(chunk)<=max_length:
            yield chunk
        else:
            for chunk_i in recursive_split(chunk, max_length, split_characters[1:], final_split_character):
                yield chunk_i
    

def scrape_website(url_str):
    
    URL = urlparse(url_str)
    
    website_dir = os.path.join(data_dir, URL.hostname, URL.path[1:]) # strip leading / off of path
    
    os.makedirs(website_dir) # error on already existing page scrape?
    
    print('Writing website to:', website_dir)
    
    page_content = requests.get(url_str).text#content#.decode("utf-8")
    
    with open(os.path.join(website_dir, 'content.html'), 'w') as f:
        f.write(page_content)
    
    page_content_doc = Document(page_content)
    page_content_dom = BeautifulSoup(page_content_doc.content().strip("'b"), features="lxml") # summary remove all the junk in the html, leaves just the article
    page_content_text = page_content_dom.get_text() # removes the html from the article
    
    with open(os.path.join(website_dir, 'text_content'), 'w') as f:
        f.write(page_content_text.replace('\\n', ' ').replace('\n', ' ').replace('\t', ' ').replace('  ', ' ').replace('  ', ' '))
    
    # now, chunk the doc for vectorization
    
    max_chunk_size = 500
    # recursive_split(page_content_text, max_chunk_size, ['\n\n\n', '\n\n', '\n'], '. ')
    chunks = [ c
        for c in page_content_text
        .replace('\\n', ' ').replace('\n', ' ')
        .replace('\\t', ' ').replace('\t\t', '').replace('\t\t', '').replace('\t\t', '').replace('\t', ' ')
        .replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ')
        .replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ')
        .split('. ')
        if len(c)!=0
    ]
    
    print(chunks)
    
    embeddings = []
    for c, e in tqdm(
        zip(
            chunks,                         # , task_type='RETRIEVAL_QUERY'
            encode_text_to_embedding_batched([ TextEmbeddingInput(text=c) for c in chunks ])[1]
        ),
        total=len(chunks),
        desc="Chunk --> Embedding",
    ):
        id_chunk = str(hash(c))
        
        # Append to file
        embeddings.append(json.dumps(
            {
                "id": id_chunk,
                "embedding": [str(value) for value in e],
                "text": c
            }
        ))
        
    with open(os.path.join(website_dir, 'embeddings.jsonl'), "a") as f:
        f.write('\n'.join(embeddings))
    

#scrape_website('https://en.wikipedia.org/wiki/Murshidabad')

scrape_website('https://admissions.utah.edu/information-resources/residency/residency-state-exceptions/')
