import os
import shutil
from dotenv import load_dotenv
from typing import Optional

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.models import LlmResponse, LlmRequest
from google.adk.agents.callback_context import CallbackContext
from google.api_core.client_options import ClientOptions
from google.cloud import modelarmor_v1 as aiplatform
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import  SseServerParams 
# from mcp import StdioServerParameters
# Import SequentialAgent for code pipeline agent
from google.adk.agents.sequential_agent import SequentialAgent
 # Ensure wiz_agent is imported to set up environment variables
from google.adk.agents import LlmAgent
load_dotenv()

# This is a robust way to find the path programmatically
uv_path = shutil.which("uv")

if not uv_path:
    raise FileNotFoundError("Could not find the 'uv' executable in the system's PATH.")

project = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION")
endpoint_id = os.getenv("AIP_ENDPOINT_ID")
client_id = os.getenv("WIZ_CLIENT_ID")
client_secret = os.getenv("WIZ_CLIENT_SECRET")

client = aiplatform.ModelArmorClient(
    transport="rest",
    client_options=ClientOptions(api_endpoint=f"modelarmor.{location}.rep.googleapis.com")
)

def model_armor_analyze(prompt: str):
    #get_data = wiz_agent.request_wiz_api_token(client_id, client_secret)
    print(f"Analyzing prompt with Model Armor: {prompt}")
    print(f"Using Model Armor endpoint: projects/{project}/locations/{location}/templates/{endpoint_id}")
    user_prompt_data = aiplatform.DataItem(text=prompt)
    request = aiplatform.SanitizeUserPromptRequest(
        name=f"projects/{project}/locations/{location}/templates/{endpoint_id}",
        user_prompt_data=user_prompt_data
    )
    
    response = client.sanitize_user_prompt(request=request)
    print(response)
    
    jailbreak = response.sanitization_result.filter_results.get("pi_and_jailbreak")
    sensitive_data = response.sanitization_result.filter_results.get("sdp")
    malicious_content = response.sanitization_result.filter_results.get("malicious_uris")

    return jailbreak, sensitive_data, malicious_content

def guardrail_function(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    agent_name = callback_context.agent_name
    print(f"[Callback] Before model call for agent: {agent_name}")

    pii_found = callback_context.state.get("PII", False)

    last_user_message = ""
    if llm_request.contents and llm_request.contents[-1].role == 'user':
        if llm_request.contents[-1].parts:
            last_user_message = llm_request.contents[-1].parts[0].text
    print(f"[Callback] Inspecting last user message: '{last_user_message}'")

    if pii_found and str(last_user_message).lower() != "yes":
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Please respond Yes/No to continue")]
            )
        )
    elif pii_found and str(last_user_message).lower() == "yes":
        callback_context.state["PII"] = False
        return None

    jailbreak, sensitive_data, malicious_conntent = model_armor_analyze(str(last_user_message))
    if sensitive_data and sensitive_data.sdp_filter_result and sensitive_data.sdp_filter_result.inspect_result:
        if sensitive_data.sdp_filter_result.inspect_result.match_state.name == "MATCH_FOUND":
            pii_found = True
            callback_context.state["PII"] = True
            if pii_found and str(last_user_message).lower() != "No":
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=
                                          f"""
                                          Your query has identify the following personal information:
                                          {sensitive_data.sdp_filter_result.deidentify_result.info_types}
                                          
                                          Would you like to continue? (Yes/No)
                                          """
                                          )],
                    )
                )
            elif pii_found and str(last_user_message).lower() == "Yes":
                callback_context.state["PII"] = False
                return None
            elif pii_found and str(last_user_message).lower() == "No":
                callback_context.state["PII"] = False
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text="Please rephrase your query without personal information.")],
                    )
                )

    if jailbreak and jailbreak.pi_and_jailbreak_filter_result.match_state.name == "MATCH_FOUND":
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="""Break Reason: Jailbreak""")]
            )
        )
    if malicious_conntent and malicious_conntent.malicious_uri_filter_result.match_state.name == "MATCH_FOUND":
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="""Break Reason: Malicious Content""")]
            )
        )
    return None

# Define wiz agent 
# PATH_TO_YOUR_MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), 'wiz-mcp', 'src', 'wiz_mcp_server', 'wiz_mcp_server.py')

wiz_agent = LlmAgent(
    name= "wiz_agent",
    model="gemini-2.5-pro",
    description="You are an Wiz agent that will get the issues from wiz security platform and generate remediation code.",
    instruction="You are a helpful assistant that takes infomation from wiz security platform and generates remediation code and emails it to list of users.",
    before_model_callback=guardrail_function,
    tools=[
        MCPToolset(
            connection_params=SseServerParams(
                url="http://localhost:8001/sse"
            )
        )
    ]
)

# Define search agent
gemini_agent = Agent(
    name="gemini_agent",
    model="gemini-2.5-pro",
    description="You will provide intelligence on security issues",
    instruction="You are a helpful assistant that takes infomation from wiz security platform and generates remediation code and emails it to list of users.",
    before_model_callback=guardrail_function,
    tools=[
        google_search
    ]
)
# Define mail agent 
mail_agent = Agent(
    name="mail_agent",
    model="gemini-2.5-pro",
    description="You are an mail agent to create and send email",
    instruction="You are a helpful assistant that takes infomation and create an emails that could be sent to list of users."       
)

# Define code pipeline agent that chains the above agents
search_agent = SequentialAgent(
    name="search_agent",
    sub_agents=[wiz_agent,gemini_agent, mail_agent], 
    description="Executes a sequence of search , reviewing, and refactoring.",
    # The agents will run in the order provided: serch -> wiz_agent_path -> Mail agent 
)

# For ADK tools compatibility, the root agent must be named `root_agent`
root_agent = search_agent
