
import vertexai
from vertexai.language_models import ChatModel, InputOutputTextPair, ChatSession, ChatMessage, TextGenerationModel

vertexai.init(project="stone-botany-397219", location="us-central1")


#response = chat.send_message("""I want to return my order. What\'s your return policy?""", **parameters)
#print(f"Response from Model: {response.text}")
#response = chat.send_message("""I ordered 30 days ago. Could you please help me with an exception? I was traveling abroad.""", **parameters)
#print(f"Response from Model: {response.text}")
#print(chat.message_history)

chat_model = ChatModel.from_pretrained("chat-bison")
language_model = TextGenerationModel.from_pretrained("text-bison")

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
            message_history=[]  # since there is no database of old messages currently...
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

class AgentChatMessage():
    
    def __init__(self, content, agent_name):
        self.content = content
        self.agent_name = agent_name
    
    def get_formatted_message(self):
        return self.agent_name+': '+self.content
    
    def to_dict(self):
        return {'content': self.content, 'name': self.agent_name}

class AgentChatSession():
    
    def __init__(self, message_history):
        self.message_history = message_history
        self.member_list = dict()
        
    def composite_message_history(self):
        return '\n'.join([m.get_formatted_message() for m in self.message_history])
    
    def user_message_event(self, user, message):
        self.message_history.append(message)
        self.member_list[user.user_id] = user
        
    def get_context(self):
        users = [ self.member_list[a].get_name() for a in self.member_list if type(a)==User ]
        agents = [ self.member_list[a].get_name() for a in self.member_list if type(a)==Agent ]
        ret = f'''The following is a transcript from a conversation with the following user(s):
{', '.join(users)}
And the following chat bot agent(s):
{', '.join(agents)}'''
        return ret
    
    def get_agent_response(self, agent, record_response=True):
        self.member_list[agent.agent_name] = agent
        prompt = self.get_context() + '\n' + agent.context + '\nTranscript:'+ '\n\n' + self.composite_message_history() + '\n' + agent.agent_name + ': '
        print('Prompt:')
        print(prompt)
        response = agent.model.predict(
            prompt=prompt,
            stop_sequences=[ self.member_list[a].get_name()+':' for a in self.member_list ],
            **agent.prediction_parameters
        )
        message = AgentChatMessage(
            content=response.text,
            agent_name=agent.agent_name
        )
        if record_response:
            self.message_history.append(message)
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

def DelagationAgent(chat_session, default_agent, agents_description_lookup):
    description_categories_string = '\n'.join([ a + ': ' + agents_description_lookup[a] for a in agents ])
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
    
    k = chat_session.get_agent_response(agent, record_response=False).content
    if k in agents_description_lookup.keys():
        return agents_description_lookup[k]
    return default_agent

def on_message(user_id, message, html_document, page):
    
    # should lock threads on user_id
    
    if user_id in users:
        user = users[user_id]
    else:
        user = User(user_id)
        user.load_chat_session()
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
    
    message_from_user = AgentChatMessage(content=message, agent_name=user.user_id)
    new_messages.append(message_from_user.to_dict())
    chat_session.user_message_event(user, message_from_user)
    
    more_information_agent = RequestMoreInformationAgent()
    rephase_agent = RephraseQuestionAgent()
    thought_agent = InternalThoughtAgent()
    qaagent = QAAgent()
    
#    leader = DelagationAgent(
#        [more_information_agent, rephase_agent, thought_agent, qaagent]
#    )
#
#
    
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
