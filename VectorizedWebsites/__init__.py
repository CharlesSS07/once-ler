
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markdownify import markdownify as md
import re
import pandas as pd
import os
import glob
import json
import math
import functools
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Generator, List, Tuple, Optional
import numpy as np
from tqdm.auto import tqdm

import vertexai
from vertexai.language_models import TextEmbeddingModel, TextEmbeddingInput
vertexai.init(project="stone-botany-397219", location="us-central1")

cache_dir = os.path.join(os.path.split(__file__)[0], 'cache')
if not os.path.exists(cache_dir):
    os.mkdir(cache_dir)

def get_website_cache_file(url:str, filename):
    
    URL = urlparse(url)
    
    sep = '|'
    
    path = [URL.hostname, *[ f for f in URL.path.split('/') if len(f)!=0 ], filename]
    
    website_dir = os.path.join(cache_dir, sep.join(path)) # strip leading / off of path
    
#    print(website_dir, path)
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

def pre_chunk_clean(text):
    text = re.sub(r'\\\\n', '\n', text)
    text = re.sub(r'\\\\t', '\t', text)
    text = re.sub(r'\\n', '\n', text)
    text = re.sub(r'\\t', '\t', text)
    text = re.sub(r'\n\n[\n]+', '\n\n', text) # replace 2+ \n with 2 \n
    text = re.sub(r'\t\t[\t]+', '\t\t', text) # replace 2+ \t with 2 \t
    text = re.sub(r'  [ ]+', '  ', text) # replace 2+ spaces with 2 spaces
    text = re.sub(r'---[-]+', '', text) # replace 3+ - with ---
    return text

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

def parse(url:str, page_readability_html: str, page_document_html: str):
    
    if len(glob.glob(get_website_cache_file(url, '*')))!=0:
        # have already scraped this site...
        print('cached files found for ', url)
        return # "cached"...
    
    document = BeautifulSoup(page_document_html, features="lxml")
    document.find(id='chatinterface').decompose() # remove the chat interface
    
    for element in document.find('script'):
        element.decompose()
    for element in document.find('noscript'):
        element.decompose()
    
    with open(get_website_cache_file(url, 'content.html'), 'w') as f:
        f.write(page_document_html)
    
    with open(get_website_cache_file(url, 'content.html.md'), 'w') as f:
        f.write(pre_chunk_clean(md(str(document.find('body')))))
    
    with open(get_website_cache_file(url, 'content.readability.html'), 'w') as f:
        f.write(page_readability_html)
    
    page_text = pre_chunk_clean(md(page_readability_html))
    with open(get_website_cache_file(url, 'content.readability.md'), 'w') as f:
        f.write(page_text)
    
    # parse out links, buttons, etc.
    metas = [ meta.attrs['content'] for meta in document.find_all('meta') if 'name' in meta.attrs and 'description' in meta.attrs['name'] ]
    titles = [ e.get_text() for e in document.find_all('title') ]
    
    print('Meta Titles', titles)
    print('Meta Tag Descriptions',  metas)
    
    # TODO: make another table of links/buttons in the page, and the href text or surrounding text for the link/button
    # TODO: make a page summary txt (for pages smaller than x) by summarizing overlapping chunks into a running summary
    # TODO: perhaps a second page summary which takes into account all the href text used by links which lead to it
    
    # now, chunk the doc for vectorization
    
    max_chunk_size = 200
    chunks = list(overlap_split(page_text, max_chunk_size, 100))
    
    print(chunks)
    
#    embeddings = pd.DataFrame(columns=['embeddings', 'chunks'])
    with open(get_website_cache_file(url, 'content.readability.md.embeddings.json'), 'a') as f:
        for i, (c, e) in tqdm(
            enumerate(zip(
                chunks,                         # , task_type='RETRIEVAL_QUERY'
                encode_text_to_embedding_batched([ TextEmbeddingInput(text=c) for c in chunks ])[1]
            )),
            total=len(chunks),
            desc="Chunk --> Embedding",
        ):
            embeddings_formatted = [
                json.dumps(
                    {
#                        "id": hash(c),
                        "embedding": e,
                        "chunk": c,
#                        "site": url
                    }
                ) + '\n'
            ]
            f.writelines(embeddings_formatted)
        
        # Append to file
#        embeddings.loc[i] = {
#            "embeddings": e,
#            "chunks": c
#        }
    
#    embeddings.to_pickle(os.path.join(website_dir, 'embeddings.pkl'))

#scrape_website('https://en.wikipedia.org/wiki/Murshidabad')

#parse('https://admissions.utah.edu/information-resources/residency/residency-state-exceptions/', 'XYZ', 'XYZ')

def load_website_vectors(url: str):
    
    # check if website_dir exists...
    embeddings = pd.DataFrame(columns=['embedding', 'chunk'])
    with open(get_website_cache_file(url, 'content.readability.md.embeddings.json'), 'r') as f:
        for i, line in enumerate(f.readlines()):
            embeddings.loc[i] = json.loads(line)
    return embeddings
#    return pd.read_pickle(os.path.join(get_website_cache(url), 'embeddings.pkl'))
