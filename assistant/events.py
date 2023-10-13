
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
from sentence_transformers.util import cos_sim

users = {}

uuagent = assistant.agents.UUExternalCustomerServiceAgent()

def on_user_message(user_id, message, url):
    
    # should lock threads on user_id
    
    new_messages = []
    
    try:
        
        if user_id in users:
            user = users[user_id]
        else:
            user = assistant.conversation.User(user_id)
            user.load_chat_session()
            users[user_id] = user
        
        escape_code = '%EVAL' # <-- hella dangerous
        if message.startswith(escape_code):
            scope = {**globals(), **locals()}
            output = eval(message[len(escape_code):], scope)
            print('EVAL: ', output)
            return [{'content': str(output), 'name': 'system'}]
        
        chat_session = user.chat_session
        
        message_from_user = assistant.conversation.GroupChatMessage(content=message, sender=user)
        new_messages.append(message_from_user.to_dict())
        chat_session.user_message_event(user, message_from_user)
        
        # load this websites vector store
        page_data = websitedata.ProcessedWebpageCache(url).load()
        
#        # embed message and look up similar ones
#        message_embedding = websitedata.embedding_model.encode([message])[0].astype(float)
#        chunk_rank = np.array(cos_sim(message_embedding, np.array(list(page_data.embedding))))[0]
#        chunk_rank_order = np.argsort(chunk_rank)[::-1][:7]
#        print('chunk_rank_ordered', chunk_rank[chunk_rank_order])
#        top_chunks = page_data.chunk[chunk_rank_order]
#
#        print("Pre-Strip:", '...\n\n\n\n...'.join([ str(i) for i in top_chunks[chunk_rank[chunk_rank_order]>0.65] ]))
#        background_info = tools.async_api_calls(
#            tools.strip_info,
#            [
#                (chunk, message)
#                for chunk in top_chunks[chunk_rank[chunk_rank_order]>0.80]
#            ]
#        )
#        print("Background Info:", '\n\n'.join(background_info))
#        background_info = [
#            '- '+info
#            for info in background_info
#            if not 'IRRELEVANT' in info
#        ]
#        print("Background Info:", '\n\n'.join(background_info))
        
        class MrWebpage(assistant.agents.ProperNoun):
            def get_name(self):
                return "Webpage"
        webpage_agent = MrWebpage()
#
#        if len(background_info)>0:
#
#            chat_session.message_history.send_message(
#                assistant.conversation.GroupChatMessage(
#                    content='\n\n'.join(background_info),
#                    sender=webpage_agent
#                )
#            )
#
#        else:
#
#            failed_to_find_info_message = assistant.conversation.GroupChatMessage(
#                content='The user has asked a question for which the website does not have an answer. Therefore, Mr. University of Utah should inform the user of this, referencing the part of the quesiton which could not be answered.',
#                sender=webpage_agent
#            )
#            chat_session.message_history.send_message(failed_to_find_info_message)
#            new_messages.append(failed_to_find_info_message.to_dict())

        chat_session.message_history.send_message(
            assistant.conversation.GroupChatMessage(
                content=page_data.get_summary(),
                sender=webpage_agent
            )
        )
        
        message_from_uuagent = chat_session.get_agent_response(uuagent)
        new_messages.append(message_from_uuagent.to_dict())
        
        return new_messages
    
    except Exception as e:
        traceback.print_exc()
        return [ *new_messages,
            {'content': "<b>ERROR</b>", 'name': 'system'},
            {'content': str(e), 'name': 'system'},
            # {'content': "Try Again Later!", 'name': 'system'}
        ]
