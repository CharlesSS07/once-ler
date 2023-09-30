import time

import vertexai
from vertexai.language_models import TextGenerationModel, TextEmbeddingModel

vertexai.init(project="stone-botany-397219", location="us-central1")


#response = chat.send_message("""I want to return my order. What\'s your return policy?""", **parameters)
#print(f"Response from Model: {response.text}")
#response = chat.send_message("""I ordered 30 days ago. Could you please help me with an exception? I was traveling abroad.""", **parameters)
#print(f"Response from Model: {response.text}")
#print(chat.message_history)

#chat_model = ChatModel.from_pretrained("chat-bison")
language_model = TextGenerationModel.from_pretrained("text-bison")
embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")
#chat = chat_model.start_chat(
#    context="""You are a customer service representative helping an internet user understand a website.""",
#    examples=[
#        InputOutputTextPair(
#            input_text="""I was in a car accident last month and couldn\'t return the item in the 30 days time window. Can you make an exception for me?""",
#            output_text="""I understand that you had an emergency and were unable to return your order within the 30-day window. I would be happy to make an exception for you. Please contact our customer service department at 1-555-010--2667 and they will be able to assist you with your return.
#Once your return is approved, you will be issued a return label. Please pack the item carefully and ship it back to us. We will process your refund within 3-5 business days of receiving the returned item."""
#        ),
#        InputOutputTextPair(
#            input_text="""I forgot to return the item within 30 days. Can you make an exception for me?""",
#            output_text="""I understand that you want to return the item, but we are unable to return your order since you have missed the 30-day window. Please let me know anything else I can assist you with."""
#        )
#    ]
#)

users = {}

class ProperNoun():
    
    def get_name(self):
        raise Exception('The get_name method of a ProperNoun must be implemented!')

class User(ProperNoun):
    
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

class Agent(ProperNoun):
    
    def __init__(self, model, agent_name, context, prediction_parameters):
        self.model = model
        self.agent_name = agent_name
        self.context = context
        self.prediction_parameters = prediction_parameters
    
    def __str__(self):
        return 'Agent: '+self.agent_name
    
    def get_name(self):
        return self.agent_name
        
#    def comment(self, chat_session):
#        

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
    '''
    Tracks messages in a single conversation. Uses a permissions system to return a subset of
    messages which the accessor is "allowed" to see. This allows for the construction of complex
    message histories which are different for different accessors. A feature such as this is
    useful for group chat bots because not every chat bot should be able to see the thoughts,
    ramblings, and auxiliary information of every other chat bot. Doing so allows me to create
    even bigger group chats.
    '''
    
    public_scope = object()
    
    class ScopedGroupChatMessage():
        
        def __init__(self, message, scopes):
            self.message = message
            self.scopes = scopes
    
    def __init__(self):
        self.scopes = {MessageHistory.public_scope: set()}
        self.message_history = []
    
    def register_agent(self, agent):
        self.add_to_scope(agent, MessageHistory.public_scope)
    
    def add_to_scope(self, agent, scope_key):
        if not scope_key in self.scopes.keys():
            self.scopes[scope_key] = set()
        self.scopes[scope_key].add(agent)
        
    def get_visible_messages(self, agent_accessor):
        for m in self.message_history:
            print(m.message.content)
            for scope in m.scopes:
                print(scope)
                if scope in self.scopes.keys() and agent_accessor in self.scopes[scope]:
                    print('match found!')
                    yield m.message
                    break # don't return same message twice if agent is in multiple scopes
    
    def text_transcript(self, agent_accessor):
        return '\n'.join(
        [ m.get_formatted_message() for m in self.get_visible_messages(agent_accessor) ])
    
    def full_text_transcript(self):
        return '\n'.join(
        [ m.get_formatted_message() for m in self.message_history ])
    
    def send_message(self, message, access_scopes=None):
        if access_scopes==None:
            access_scopes = [MessageHistory.public_scope]
        self.message_history.append(MessageHistory.ScopedGroupChatMessage(message, access_scopes))

class AgentChatSession():
    
    def __init__(self, message_history):
        self.message_history = message_history
        self.member_list = dict()
    
    def user_message_event(self, user, message):
        self.message_history.send_message(message)
        self.member_list[user.user_id] = user
        
    def get_context(self):
        users = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==User ]
        agents = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==Agent ]
        print(len(users), print(len(agents)))
        ret = f'''The following is a transcript from a conversation with the following user(s):
{', '.join(users)}
And the following chat bot agent(s):
{', '.join(agents)}'''
        return ret
    
    def get_agent_response(self, agent, record_response=True):
        self.member_list[agent.agent_name] = agent
        prompt = agent.context + '\n' + self.get_context() + '\n\nTranscript:\n' + self.message_history.text_transcript(agent) + '\n' + agent.agent_name + ': '
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
        

def RephraseQuestionAgent():
    return Agent(
        model=language_model,
        context='You are a customer service bot who rephrases the most recent question using context fropm the entire conversation.',
        agent_name='Mr. Rephrase',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )

def RequestMoreInformationAgent():
    return Agent(
        model=language_model,
        context='You are a customer service bot who prompts the user for more information, if required. If there is not enough informaiton, specify what information the user should provide. If there is enough information, respond with "LOOKS GOOD!".',
        agent_name='Mr. More Information Please',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )

def QAAgent():
    return Agent(
        model=language_model,
        context='You are a customer service representative helping an internet user understand a website.',
        agent_name='Mr. Answer',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )
    
def InternalThoughtAgent():
    return Agent(
        model=language_model,
        context='Thoughts are not shown to the user, although help transcript readers understand what is happening in a dialogue.',
        agent_name='Internal Thought',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )

def EndofConversationAgent():
    return Agent(
        model=language_model,
        context='You are a customer service personell who is making the ending remarks to a conversation.',
        agent_name='Mr. Byebye',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )

def DoubtAgent():
    return Agent(
        model=language_model,
        context='You are a chat bot who doubts the statements of other chat bots. Explain what you doubt and why you doubt it.',
        agent_name='Mr. Doubful',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )

def delegate_agents(chat_session, default_agent, agents_description_lookup):
    description_categories_string = '\n'.join([ a + ': ' + agents_description_lookup[a].context for a in agents_description_lookup ])
    agent = Agent(
        model=language_model,
        context=f'''You are a customer service agent fowarding a customer to the best customer service worker to take care of their request. Respond with one of the following options, using the description of what the worker specializes in to select the best worker for the customer request.
Options:
{ description_categories_string }

Worker: ''',
        agent_name='Leader',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )
    
    response_agent = chat_session.get_agent_response(agent, record_response=False).content
    for k in agents_description_lookup.keys():
        if k in response_agent or response_agent in k:
            print(response_agent, 'found')
            return agents_description_lookup[k]
    print(response_agent, 'not found')
    return default_agent

more_information_agent = RequestMoreInformationAgent()
rephase_agent = RephraseQuestionAgent()
thought_agent = InternalThoughtAgent()
qaagent = QAAgent()
eoc = EndofConversationAgent()
doubtagent = DoubtAgent()

import os
from urllib.parse import urlparse
import json
import numpy as np
data_dir = os.path.join(os.path.split(__file__)[0], 'VectorizedWebsites')
def load_vectordb(url_str):
    
    URL = urlparse(url_str)
    
    website_dir = os.path.join(data_dir, URL.hostname, URL.path[1:])
    
    # check if website_dir exists...
    
    embeddings = []
    texts = []
    with open(os.path.join(website_dir, 'embeddings.jsonl'), 'r') as f:
        for line in f.readlines():
            data = json.loads(line)
            embeddings.append(data['embedding'])
            texts.append(data['text'])
    
    return np.array(texts), np.array(embeddings).astype(float)

utah_residency_page_chunks, utah_residency_page_embeddings = load_vectordb('https://admissions.utah.edu/information-resources/residency/residency-state-exceptions/')

def on_message(user_id, message, html_document, page):
    
    # should lock threads on user_id
    
    if user_id in users:
        user = users[user_id]
    else:
        user = User(user_id)
        user.load_chat_session()
        for agent in [more_information_agent, rephase_agent, thought_agent, qaagent, eoc, doubtagent, user]:
            user.chat_session.message_history.register_agent(agent)
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
    
    # embed message and look up similar ones
    message_embedding = np.array(embedding_model.get_embeddings([message])[0].values).astype(float)
    chunk_rank = np.dot(message_embedding, utah_residency_page_embeddings.T)
    print('chunk_rank', chunk_rank[np.argsort(chunk_rank)[::-1][:7]])
    background_info = '\n'.join(utah_residency_page_chunks[np.argsort(chunk_rank)[::-1][:7]])
    print("Background Info:", background_info)
    
    if chunk_rank[-1]>0.55:
        class BackgroundSupplier(ProperNoun):
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
    
    message_from_more_information_agent = chat_session.get_agent_response(more_information_agent)
    new_messages.append(message_from_more_information_agent.to_dict())

    if not 'LOOKS GOOD!' in message_from_more_information_agent.content:
        return new_messages

    message_from_rephase_agent = chat_session.get_agent_response(rephase_agent)
    new_messages.append(message_from_rephase_agent.to_dict())

    message_from_thought_agent = chat_session.get_agent_response(thought_agent)
    new_messages.append(message_from_thought_agent.to_dict())

    message_from_qaagent = chat_session.get_agent_response(qaagent)
    new_messages.append(message_from_qaagent.to_dict())
    
    # would optimally log these to a database under the user and page. but this is MVP...
    
    return new_messages
