import time


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
        return self.user_id

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
    
    def text_transcript(self, agent_accessor):
        return '\n'.join([ m.get_formatted_message() for m in self.message_history ])
    
    def send_message(self, message):
        self.message_history.append(message)

class AgentChatSession():
    
    def __init__(self, message_history):
        self.message_history = message_history
        self.member_list = dict()
    
    def user_message_event(self, user, message):
        self.message_history.send_message(message)
        self.member_list[user.user_id] = user
        
    def get_context(self):
        users = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==User ]
        agent_list = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==agents.Agent ]
        print(len(users), print(len(agent_list)))
        ret = f'''The following is a transcript from a conversation with the following user(s):
{', '.join(users)}
And the following chat bot agent(s):
{', '.join(agent_list)}'''
        return ret
    
    def get_agent_response(self, agent, record_response=True):
        self.member_list[agent.agent_name] = agent
        prompt = str(agent.context) + '\n' + str(self.get_context()) + '\n\nTranscript:\n' + self.message_history.text_transcript(agent) + '\n' + str(agent.agent_name) + ': '
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

more_information_agent = agents.RequestMoreInformationAgent()
rephase_agent = agents.RephraseQuestionAgent()
thought_agent = agents.InternalThoughtAgent()
qaagent = agents.QAAgent()
eoc = agents.EndofConversationAgent()
doubtagent = agents.DoubtAgent()
uuagent = agents.UUExternalCustomerServiceAgent()

import os
from urllib.parse import urlparse
import json
import numpy as np
import pandas as pd
data_dir = os.path.join(os.path.split(__file__)[0], 'VectorizedWebsites')

def load_website_vectors(url_str):
    
    URL = urlparse(url_str)
    
    website_dir = os.path.join(data_dir, URL.hostname, URL.path[1:])
    
    # check if website_dir exists...
    
    return pd.read_pickle(os.path.join(website_dir, 'embeddings.pkl'))

def on_user_message(user_id, message, page):
    
    # should lock threads on user_id
    
    if user_id in users:
        user = users[user_id]
    else:
        user = User(user_id)
        user.load_chat_session()
#        for agent in [more_information_agent, rephase_agent, thought_agent, qaagent, eoc, doubtagent, user]:
#            user.chat_session.message_history.register_agent(agent)
#            user.chat_session.message_history.add_to_scope(agent, 'user')
        users[user_id] = user
    
    escape_code = '%EVAL' # <-- hella dangerous
    if message.startswith(escape_code):
        scope = {**globals(), **locals()}
        try:
            print('EVAL: ', eval(message[len(escape_code):], scope))
        except Exception as e:
            print(e) # print stack trace...
        return [{'content': 'Evaluated Successfully.', 'name': 'system'}]
    
    chat_session = user.chat_session
    
    new_messages = []
    
    message_from_user = GroupChatMessage(content=message, sender=user)
    new_messages.append(message_from_user.to_dict())
    chat_session.user_message_event(user, message_from_user)
    
#    message_from_uuagent = chat_session.get_agent_response(uuagent)
#    new_messages.append(message_from_uuagent.to_dict())
    
    # load this websites vector store
    page_data = load_website_vectors(page)
    
    # embed message and look up similar ones
    message_embedding = np.array(embedding_model.get_embeddings([message])[0].values).astype(float)
    print(message_embedding.shape, np.array(list(page_data.embeddings)).shape)
    chunk_rank = np.dot(message_embedding, np.array(list(page_data.embeddings)).T)
    chunk_rank_order = np.argsort(chunk_rank)[::-1][:7]
    print('chunk_rans_ordered', chunk_rank[chunk_rank_order])
    top_chunks = page_data.chunks[chunk_rank_order]
    background_info = '\n'.join(top_chunks[chunk_rank[chunk_rank_order]>0.6])
    print("Background Info:", background_info)
    
    if len(background_info)>0:
        class BackgroundSupplier(agents.ProperNoun):
            def get_name(self):
                return "Mr. Background"
        
        chat_session.message_history.send_message(
            GroupChatMessage(
                content=background_info,
                sender=BackgroundSupplier()
            )
        )
    
#    for i in range(10):
#
#        delegate = delegate_agents(
#            chat_session,
#            eoc,
#            { a.agent_name: a for a in [ more_information_agent, rephase_agent, thought_agent, qaagent, eoc, doubtagent ] }
#        )
#
#        message_from_delegate = chat_session.get_agent_response(delegate)
#        new_messages.append(message_from_delegate.to_dict())
#
#        if delegate==eoc:
#            return new_messages
    
#    message_from_more_information_agent = chat_session.get_agent_response(more_information_agent)
#    new_messages.append(message_from_more_information_agent.to_dict())
#    if not 'LOOKS GOOD!' in message_from_more_information_agent.content:
#        return new_messages

#    message_from_rephase_agent = chat_session.get_agent_response(rephase_agent)
#    new_messages.append(message_from_rephase_agent.to_dict())

    message_from_thought_agent = chat_session.get_agent_response(thought_agent)
    new_messages.append(message_from_thought_agent.to_dict())
    
    message_from_uuagent = chat_session.get_agent_response(uuagent)
    new_messages.append(message_from_uuagent.to_dict())

#    message_from_qaagent = chat_session.get_agent_response(qaagent)
#    new_messages.append(message_from_qaagent.to_dict())
    
    # would optimally log these to a database under the user and page. but this is MVP...
    
    return new_messages
