import glob
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import MessageRole, FilePurpose, FunctionTool, FileSearchTool, ToolSet
from dotenv import load_dotenv
#
load_dotenv(override=True)
project_client = AIProjectClient(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential()
)
AGENT_INSTRUCTIONS = """
Start with a friendly greeting.
You are an agent that helps customers order pizzas from Contoso pizza.
Get the locations of Contoso Pizza retail stores from uploaded file.
You have a Gen-alpha personality, so you are friendly and helpful, but also a bit cheeky.
You can provide information about Contoso Pizza and its retail stores.
You help customers order a pizza of their chosen size, crust, and toppings.
You don't like pineapple on pizzas, but you will help a customer a pizza with pineapple ... with some snark.
Make sure you know the customer's name before placing an order on their behalf.
You can't do anything except help customers order pizzas and give information about Contoso Pizza. You will gently deflect any other questions.
"""
# Upload file and create vector store
store_files = glob.glob("/workspaces/open-hack-agents-codespace/StoreLocations/*")
if not store_files:
    raise FileNotFoundError("No files found in ./StoreLocations/")

uploaded_file_ids = []
for path in store_files:
    print(f"File: {path}")    
    uploaded = project_client.agents.files.upload(file_path=path, purpose=FilePurpose.AGENTS)
    uploaded_file_ids.append(uploaded.id)

print(f"Uploaded files: {uploaded_file_ids}")

vector_store = project_client.agents.vector_stores.create_and_poll(file_ids=uploaded_file_ids, name="PizazaStoreLocationsVector")

# Create file search tool and agent
file_search = FileSearchTool(vector_store_ids=[vector_store.id])


agent = project_client.agents.create_agent(
    model="gpt-4o",
    name="my-agent-PIZZA",
    instructions=AGENT_INSTRUCTIONS,
    tools=file_search.definitions,
    tool_resources=file_search.resources,
)

print(f"Created agent, ID: {agent.id}")
thread = project_client.agents.threads.create()
print(f"Created thread, ID: {thread.id}")

while True:

    # Get the user input
    user_input = input("You: ")

    # Break out of the loop
    if user_input.lower() in ["exit", "quit"]:
        break

    # Add a message to the thread
    message = project_client.agents.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER, 
        content=user_input
    )

    run = project_client.agents.runs.create_and_process(
        thread_id=thread.id, 
        agent_id=agent.id
    )    

    messages = project_client.agents.messages.list(thread_id=thread.id)  
    first_message = next(iter(messages), None) 
    if first_message: 
        print(next((item["text"]["value"] for item in first_message.content if item.get("type") == "text"), ""))
        
project_client.agents.vector_stores.delete(vector_store.id)

project_client.agents.delete_agent(agent.id)
print("Deleted agent")