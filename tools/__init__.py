
from concurrent.futures import ThreadPoolExecutor
import functools

from vertexai.preview.language_models import TextGenerationModel

language_model = TextGenerationModel.from_pretrained("text-bison")

def combine_and_summarize(text1, text2):
    return language_model.predict(
        prompt=f'''Combine, and summarize the following raw text. Do not state any thing twice.
Text 1: {text1}
Text 2: {text2}
Summary: ''',
        **{
            'max_output_tokens':512,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    ).text.strip()

def summarize(text):
    return language_model.predict(
        prompt=f'''Summarize the following raw text. It may contain partial information which should be ignored:
{text}

Summary: ''',
        **{
            'max_output_tokens':512,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    ).text.strip()

def strip_info(text, query):
    return language_model.predict(
        prompt=f'''What does the following raw text say about "{query}"? Use only information from the text to answer. If the text does not contain useful information, respond with "IRRELEVANT".
Text: {text}

Relevant pieces: ''',
        **{
            'max_output_tokens':512,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    ).text.strip()

def async_api_calls(api, packets):
    '''
    Uses threads to asyncronously call api.
    api should be an api call, not a something which requires an entire processor.
    packes is a list. elements are an input to api.
    '''
    
    outputs = []
    with ThreadPoolExecutor() as executor:
        futures = [ executor.submit(functools.partial(api, i)) for i in packets ]
        outputs = [ future.result() for future in futures ]
    
    return outputs

def summarize_chunks(chunks):
    
    summaries = chunks#async_api_calls(summarize, chunks)
    
    master_summery = summaries.pop(0)
    
    while len(summaries)>0:
        master_summery = combine_and_summarize(
            master_summery, summaries.pop(0)
        )
#        print('\n\nMaster Summary:', master_summery)
    
    return master_summery
