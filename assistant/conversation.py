
import assistant

import time

class User(assistant.agents.ProperNoun):
    
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

class AgentGroupChatMessage(GroupChatMessage):
    
    def __init__(self, content, sender, prompt):
        super().__init__(content, sender)
        self.prompt = prompt
    
    def get_prompt(self):
        return self.prompt

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
        
#    def get_context(self):
#        users = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==User ]
#        agent_list = [ self.member_list[a].get_name() for a in self.member_list if type(self.member_list[a])==assistant.agents.Agent ]
#        ret = f'''The following is a transcript from a conversation with the following user(s):
#{', '.join(users)}
#And the following chat bot agent(s):
#{', '.join(agent_list)}'''
#        return ret
    
    def get_agent_response(self, agent, record_response=True):
        self.member_list[agent.agent_name] = agent
        prompt = str(agent.context) + '\n' + '\n\nTranscript:\n' + self.message_history.text_transcript() + '\n' + str(agent.agent_name) + ': '
        print('\n\n##### Prompt:')
        print(prompt)
        response = agent.complete(
            prompt=prompt,
            stop_sequences=[ self.member_list[a].get_name()+':' for a in self.member_list ]
        )
        message = AgentGroupChatMessage(
            content=response,
            sender=agent,
            prompt=prompt
        )
        if record_response:
            self.message_history.send_message(message)
        return message
