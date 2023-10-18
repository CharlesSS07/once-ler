
import tools
import assistant
import websitedata

import time
import asyncio
import traceback
import os
from urllib.parse import urlparse
import json
import numpy as np
import pandas as pd
import threading

users = {}

from vertexai.language_models import TextGenerationModel
language_model = TextGenerationModel.from_pretrained("text-bison")

class Assistant(assistant.agents.ProperNoun):
    def get_name(self):
        return "Assistant"
assistant_agent = Assistant()

def on_user_message(user_id, message, url, return_message_buffer):
    
    # should lock threads on user_id
    
    try:
        URL = websitedata.urlparse(url)
        url_id = os.path.join(URL.hostname, URL.path[1:])
        if user_id in users and url_id in users[user_id]:
            user = users[user_id][url_id]
        else:
            user = assistant.conversation.User(user_id)
            user.load_chat_session()
            if not user_id in users:
                users[user_id] = {}
            users[user_id][url_id] = user
        
        escape_code = '%EVAL' # <-- hella dangerous
        if message.startswith(escape_code):
            scope = {**globals(), **locals()}
            output = eval(message[len(escape_code):], scope)
            print('EVAL: ', output)
            return [{'content': str(output), 'name': 'system'}]
        
        chat_session = user.chat_session
        
        message_from_user = assistant.conversation.GroupChatMessage(content=message, sender=user)
#        return_message_buffer.append(message_from_user.to_dict())
        chat_session.user_message_event(user, message_from_user)
        
        print('1')
        
        # load this websites vector store
        website = websitedata.CachedWebsite(websitedata.urlparse(url).hostname)
        webpage = website.get_cached_webpage(url)
        
        print('2')
        
        summarized_webpage = websitedata.SummarizedCachedWebpage(webpage)
        summary_thread = threading.Thread(target=summarized_webpage.get_summary)
        summary_thread.start()
        
        print('3')
        
        embedded_webpage = websitedata.EmbeddedCachedWebpage(webpage)
        relevant_chunks = embedded_webpage.vector_search(message)
        
        print('4')
        
        summary_thread.join()
        
        print('5')

        if len(relevant_chunks)>0:

            page_info = '...'+'...\n\n...'.join(relevant_chunks)+'...'

            prompt = f'''You are a website assistant for the University of Utah. A student is looking at a university webpage which is summarized as follows: {summarized_webpage.get_summary()}

According to {url}:
{page_info}

This page contains some of the information the user is looking for. Tell them the information using only the given information from the webpage. Feel free to give the user URLs, and describe what the URL offers them. Do not make up information.

Transcript:
{chat_session.message_history.text_transcript()}
Answer: '''

        else:
            # in the future, this will provide a link which forards to a helpful page, but for now just tells the user that this is not the page they are looking for
            prompt = f'''You are a website assistant for the University of Utah. A student is looking at a university website which is summarized as follows: {summarized_webpage.get_summary()}

The user has asked for information which this page cannot provide.

Transcript:
{chat_session.message_history.text_transcript()}
End of transcript.

Tell the user that this page is not relevant to their search.

Example: Sorry, I can't help here because I don't know X, as it is not on this page. (X is the requested infromation)

Assistant: '''

        print(prompt)
        response = language_model.predict(
            prompt=prompt,
            stop_sequences=['User:', 'Assistant:'],
            **{
                'max_output_tokens':256,
                'temperature':0,
                'top_p':0.8,
                'top_k':40
            }
        )
        
        print('6')

        assistant_message = assistant.conversation.GroupChatMessage(
            content=response.text.strip(),
            sender=assistant_agent
        )
        return_message_buffer.append(assistant_message.to_dict())
        chat_session.message_history.send_message(assistant_message)

##        # embed message and look up similar ones
##        message_embedding = websitedata.embedding_model.encode([message])[0].astype(float)
##        chunk_rank = np.array(cos_sim(message_embedding, np.array(list(page_data.embedding))))[0]
##        chunk_rank_order = np.argsort(chunk_rank)[::-1][:7]
##        print('chunk_rank_ordered', chunk_rank[chunk_rank_order])
##        top_chunks = page_data.chunk[chunk_rank_order]
##
##        print("Pre-Strip:", '...\n\n\n\n...'.join([ str(i) for i in top_chunks[chunk_rank[chunk_rank_order]>0.65] ]))
##        background_info = tools.async_api_calls(
##            tools.strip_info,
##            [
##                (chunk, message)
##                for chunk in top_chunks[chunk_rank[chunk_rank_order]>0.80]
##            ]
##        )
##        print("Background Info:", '\n\n'.join(background_info))
##        background_info = [
##            '- '+info
##            for info in background_info
##            if not 'IRRELEVANT' in info
##        ]
##        print("Background Info:", '\n\n'.join(background_info))
#
##        class MrWebpage(assistant.agents.ProperNoun):
##            def get_name(self):
##                return "Webpage"
##        webpage_agent = MrWebpage()
##
##        if len(background_info)>0:
##
##            chat_session.message_history.send_message(
##                assistant.conversation.GroupChatMessage(
##                    content='\n\n'.join(background_info),
##                    sender=webpage_agent
##                )
##            )
##
##        else:
##
##            failed_to_find_info_message = assistant.conversation.GroupChatMessage(
##                content='The user has asked a question for which the website does not have an answer. Therefore, Mr. University of Utah should inform the user of this, referencing the part of the quesiton which could not be answered.',
##                sender=webpage_agent
##            )
##            chat_session.message_history.send_message(failed_to_find_info_message)
##            return_message_buffer.append(failed_to_find_info_message.to_dict())
#
##        chat_session.message_history.send_message(
##            assistant.conversation.GroupChatMessage(
##                content=page_data.get_summary(),
##                sender=webpage_agent
##            )
##        )
##
##        message_from_uuagent = chat_session.get_agent_response(uuagent)
##        return_message_buffer.append(message_from_uuagent.to_dict())
##
##        print(return_message_buffer)
    
    except Exception as e:
        traceback.print_exc()
        return_message_buffer.extend([
            {'content': "<b>ERROR</b>", 'name': 'system'},
            {'content': str(e), 'name': 'system'},
            # {'content': "Try Again Later!", 'name': 'system'}
        ])
