
from vertexai.language_models import TextGenerationModel
language_model = TextGenerationModel.from_pretrained("text-bison")

class ProperNoun():
    
    def get_name(self):
        raise Exception('The get_name method of a ProperNoun must be implemented!')

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

def UUExternalCustomerServiceAgent():
    return Agent(
        model=language_model,
        context='You are a customer service bot representing the University of Utah. The user has access to your website, and you are helping them find and understand what they are looking for. Always rephrase the users question, and then quote from the webpage to answer their quersion.',
        agent_name='Mr. University of Utah',
        prediction_parameters={
            'max_output_tokens':256,
            'temperature':0,
            'top_p':0.8,
            'top_k':40
        }
    )

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
        context='Thoughts are not shown to the user, although help transcript readers understand what is happening in a dialogue. Thoughts should not restate information that has already been stated elsewhere.',
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
