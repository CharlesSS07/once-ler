
import re

def clean_markdown(text):
    text = re.sub(r'\\\\n', '\n', text)
    text = re.sub(r'\\\\t', '\t', text)
    text = re.sub(r'\\n', '\n', text)
    text = re.sub(r'\\t', '\t', text)
    text = re.sub(r'[\n]+', '\n', text) # replace 2+ \n with 2 \n
    text = re.sub(r'[\t]+', '\t\t', text) # replace 2+ \t with 2 \t
    text = re.sub(r' [ ]+', '  ', text) # replace 2+ spaces with 2 spaces
    text = re.sub(r'--[-]+', '', text) # replace 3+ - with ---
    return text

def recursive_chunk(text, max_length, split_characters, final_split_character):

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

def overlap_chunk(text, max_chunk_size, chunk_overlap):
    
    l = len(text)
    
    i = chunk_overlap + max_chunk_size + chunk_overlap
    yield text[:chunk_overlap+max_chunk_size+chunk_overlap].strip()
    
    if i + max_chunk_size + chunk_overlap > l:
        return
    
    while True:
        yield text[ i - chunk_overlap : i + max_chunk_size + chunk_overlap ].strip()
        if i + max_chunk_size + chunk_overlap > l:
            break
        i += max_chunk_size
