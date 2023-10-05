import time
import asyncio
import traceback

import vertexai
from vertexai.language_models import TextGenerationModel, TextEmbeddingModel

vertexai.init(project="stone-botany-397219", location="us-central1")

import agents

embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

users = {}

class User(agents.ProperNoun):
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.about = 'No about info.'
    
    def load_chat_session(self):
        self.chat_session = AgentChatSession(
            message_history=MessageHistory()  # since there is no database of old messages currently...
        )
        return self.chat_session
    
    def get_name(self):
        return 'User'

class GroupChatMessage():
    
    def __init__(self, content, sender):
        self.content = content
        self.sender = sender
        self.timestamp = time.time()
    
    def get_formatted_message(self):
        return self.sender.get_name()+': '+str(self.content)
    
    def to_dict(self):
        return {'content': self.content, 'name': self.sender.get_name(), 'timestamp': self.timestamp}

class MessageHistory():
    
    def __init__(self):
        self.message_history = []
    
    def text_transcript(self):
        return '\n'.join([ m.get_formatted_message() for m in self.message_history ])
    
    def send_message(self, message):
        self.message_history.append(message)

class AgentChatSession():
    
    def __init__(self, message_history):
        self.message_history = message_history
        self.member_list = dict()
    
    def user_message_event(self, user, message):
        self.message_history.send_message(message)
        self.member_list[user.get_name()] = user
        
    def get_context(self):
        users = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==User ]
        agent_list = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==agents.Agent ]
        ret = f'''The following is a transcript from a conversation with the following user(s):
{', '.join(users)}
And the following chat bot agent(s):
{', '.join(agent_list)}'''
        return ret
    
    def get_agent_response(self, agent, record_response=True):
        self.member_list[agent.agent_name] = agent
        prompt = str(agent.context) + '\n' + str(self.get_context()) + '\n\nTranscript:\n' + self.message_history.text_transcript() + '\n' + str(agent.agent_name) + ': '
        print('Prompt:')
        print(prompt)
        response = agent.model.predict(
            prompt=prompt,
            stop_sequences=[ self.member_list[a].get_name()+':' for a in self.member_list ],
            **agent.prediction_parameters
        )
        message = GroupChatMessage(
            content=response.text.strip(),
            sender=agent
        )
        if record_response:
            self.message_history.send_message(message)
        return message

uuagent = agents.UUExternalCustomerServiceAgent()

import os
from urllib.parse import urlparse
import json
import numpy as np
import pandas as pd

language_model = TextGenerationModel.from_pretrained("text-bison")

def summarize(text):
    return language_model.predict(
        prompt=f'''Summarize the following raw text. It may contain partial sentences which should be ignored:
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
        prompt=f'''What does the following raw text say about "{query}":
{text}

Relevant pieces: ''',
        **{
            'max_output_tokens':512,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    ).text.strip()

import VectorizedWebsites

def on_user_message(user_id, message, page):
    
    # should lock threads on user_id
    
    try:
        
        if user_id in users:
            user = users[user_id]
        else:
            user = User(user_id)
            user.load_chat_session()
            users[user_id] = user
        
        escape_code = '%EVAL' # <-- hella dangerous
        if message.startswith(escape_code):
            scope = {**globals(), **locals()}
            output = eval(message[len(escape_code):], scope)
            print('EVAL: ', output)
            return [{'content': str(output), 'name': 'system'}]
        
        chat_session = user.chat_session
        
        new_messages = []
        
        message_from_user = GroupChatMessage(content=message, sender=user)
        new_messages.append(message_from_user.to_dict())
        chat_session.user_message_event(user, message_from_user)
        
        # load this websites vector store
        page_data = VectorizedWebsites.load_website_vectors(page)
        
        # embed message and look up similar ones
        message_embedding = np.array(embedding_model.get_embeddings([message])[0].values).astype(float)
        chunk_rank = np.dot(message_embedding, np.array(list(page_data.embedding)).T)
        chunk_rank_order = np.argsort(chunk_rank)[::-1][:7]
        print('chunk_rank_ordered', chunk_rank[chunk_rank_order])
        top_chunks = page_data.chunk[chunk_rank_order]
        background_info = '\n'.join([
            strip_info(chunk, message)
            for chunk in top_chunks[chunk_rank[chunk_rank_order]>0.65]
        ])
        print("Background Info:", background_info)
        
        class BackgroundSupplier(agents.ProperNoun):
            def get_name(self):
                return "Webpage"
        
        if len(background_info)>0:
            
            chat_session.message_history.send_message(
                GroupChatMessage(
                    content=background_info,
                    sender=BackgroundSupplier()
                )
            )

        else:
            
            failed_to_find_info_message = GroupChatMessage(
                content='The user has asked a question for which the website does not have an answer. Therefore, Mr. University of Utah should inform the user of this, referencing the part of the quesiton which could not be answered.',
                sender=BackgroundSupplier()
            )
            chat_session.message_history.send_message(failed_to_find_info_message)
            new_messages.append(failed_to_find_info_message.to_dict())
        
        message_from_uuagent = chat_session.get_agent_response(uuagent)
        new_messages.append(message_from_uuagent.to_dict())
        
        return new_messages
    
    except Exception as e:
        traceback.print_exc()
        return [ *new_messages,
            {'content': "<b>ERROR</b>", 'name': 'system'},
            {'content': str(e), 'name': 'system'}
        ]
