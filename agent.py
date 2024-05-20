import os 
import yaml
import json
import requests
from termcolor import colored
from prompts import planning_agent_prompt, integration_agent_prompt
from search import WebSearcher


def load_config(file_path):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
        for key, value in config.items():
            os.environ[key] = value

class Agent:
    def __init__(self, model, tool, temperature=0, max_tokens=1000, planning_agent_prompt=None, integration_agent_prompt=None, verbose=False):
        self.url = 'http://localhost:11434/api/generate'
        self.headers = {"Content-Type": "application/json"}
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tool = tool
        self.tool_specs = tool.__doc__
        self.planning_agent_prompt = planning_agent_prompt
        self.integration_agent_prompt = integration_agent_prompt
        self.model = model
        self.verbose = verbose

    def run_planning_agent(self, query, plan=None, outputs=None, feedback=None):
        url = self.url
        headers = self.headers

        system_prompt = self.planning_agent_prompt.format(
                outputs=outputs,
                plan=plan,
                feedback=feedback,
                tool_specs=self.tool_specs
            )

        payload = {
            "model": self.model,
            "prompt": query,
            # "format": "json",
            "system": system_prompt,
            "stream": False,
            "temperature": 0
        }

        try:
            response = requests.post(self.url, headers=headers, data=json.dumps(payload))
            response_dict = response.json()

            normal_response = response_dict['response']
            print(f"Generated Response: {normal_response}")
            return normal_response
        
        except Exception as e:
            print("Error in response:", response_dict)
            return "Error generating plan {e}"
        
    def run_integration_agent(self, query, plan=None, outputs=None, feedback=None):
        url = self.url
        headers = self.headers

        system_prompt = self.integration_agent_prompt.format(
                outputs=outputs,
                plan=plan
            )

        payload = {
            "model": self.model,
            "prompt": query,
            # "format": "json",
            "system": system_prompt,
            "stream": False,
            "temperature": 0.5
        }

        try:
            response = requests.post(self.url, headers=headers, data=json.dumps(payload))
            response_dict = response.json()

            normal_response = response_dict['response']
            print(f"Generated Response: {normal_response}")
            return normal_response
        
        except Exception as e:
            print("Error in response:", response_dict)
            return "Error generating plan {e}"
    
    def check_response(self, response, query):
        url = "http://localhost:11434/api/generate"
        # headers = {"Content-Type": "application/json"}

        payload = {
            "model": "llama3",
            "prompt": f"query: {query}\n\nresponse: {response}",
            "format": "json",
            "system": """Check if the response meets all of the requirements of the query based on the following:
                            1. The response must be relevant to the query.
                            2. The response must be coherent and well-structured.
                            3. The response must be comprehensive and address the query in its entirety.
                            4. The response must have citations and links to sources.
                            Return 'yes' if the response meets all of the requirements and 'no' otherwise.
                        The json object should have the following format:    
                        {
                            "response": "yes or no"
                        }
                        """,
            "stream": False,
            "temperature": 0.5
        }

        try: 
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            response_dict = response.json()
            response_json = json.loads(response_dict['response'])
            search_query = response_json.get('response', '')
            print(f"Response passes checks: {search_query}")

            if search_query == "yes":
                return True
            else:
                return False
        
        except Exception as e:
            print("Error in assessing response quality:", response_dict)
            return "Error in assessing response quality"
         
    def execute(self, iterations=5):
        query = input("Enter your query: ")
        tool =  self.tool(model=self.model, verbose=self.verbose)
        meets_requirements = False
        plan = None
        outputs = None
        response = None
        iterations = 0

        while not meets_requirements and iterations < 5:
            iterations += 1  
            plan = self.run_planning_agent(query, plan=plan, outputs=outputs, feedback=response)
            outputs = tool.use_tool(plan=plan, query=query)
            response = self.run_integration_agent(query, plan, outputs)
            meets_requirements = self.check_response(response, query)

        print(colored(f"Final Response: {response}", 'cyan'))

        
if __name__ == '__main__':
    agent = Agent(model="llama3",
                  tool=WebSearcher, 
                  planning_agent_prompt=planning_agent_prompt, 
                  integration_agent_prompt=integration_agent_prompt,
                  verbose=True
                  )
    agent.execute()


    
