# File server.py


import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Route, Mount

from mcp.server.fastmcp import FastMCP
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData, INTERNAL_ERROR, INVALID_PARAMS
from mcp.server.sse import SseServerTransport

import base64
import json
import requests
import os
from dotenv import load_dotenv
load_dotenv()
# Standard headers
HEADERS_AUTH = {"Content-Type": "application/x-www-form-urlencoded"}
HEADERS = {"Content-Type": "application/json"}

CLIENT_ID = os.getenv("WIZ_CLIENT_ID")
CLIENT_SECRET = os.getenv("WIZ_CLIENT_SECRET")

print(f"client id: {CLIENT_ID}")



def request_wiz_api_token(client_id, client_secret):
    """Retrieve an OAuth access token to be used against Wiz API"""

    auth_payload = {
      'grant_type': 'client_credentials',
      'audience': 'wiz-api',
      'client_id': client_id,
      'client_secret': client_secret
    }
    try:
        # Uncomment the next first line and comment the line after that
        # to run behind proxies
        # response = requests.post(url="https://auth.app.wiz.io/oauth/token",
        #                         headers=HEADERS_AUTH, data=auth_payload,
        #                         proxies=proxyDict, timeout=180)
        response = requests.post(url="https://auth.app.wiz.io/oauth/token",
                                headers=HEADERS_AUTH, data=auth_payload, timeout=180)
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")
        print(f"client id: {client_id}")
    except requests.exceptions.HTTPError as e:
        print(f"<p>Error authenticating to Wiz (4xx/5xx): {str(e)}</p>")
        raise

    except requests.exceptions.ConnectionError as e:
        print(f"<p>Network problem (DNS failure, refused connection, etc): {str(e)}</p>")
        raise

    except requests.exceptions.Timeout as e:
        print(f"<p>Request timed out: {str(e)}</p>")
        raise

    try:
        response_json = response.json()
        token = response_json.get('access_token')
        if not token:
            message = f"Could not retrieve token from Wiz: {response_json.get('message')}"
            raise ValueError(message)
    except ValueError as exception:
        message = f"Could not parse API response {exception}. Check Service Account details " \
                    "and variables"
        raise ValueError(message) from exception

    response_json_decoded = json.loads(
        base64.standard_b64decode(pad_base64(token.split(".")[1]))
    )

    response_json_decoded = json.loads(
        base64.standard_b64decode(pad_base64(token.split(".")[1]))
    )
    dc = response_json_decoded["dc"]

    return token, dc


def pad_base64(data):
    """Makes sure base64 data is padded"""
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += "=" * (4 - missing_padding)
    return data


# Create an MCP server instance with an identifier ("wiki")
mcp = FastMCP("wiz")

@mcp.tool()
def query_wiz_api(query: str, variables: dict = None) -> str:
    """
    Query Wiz API for the given query data schema.

    :param query: The GraphQL query to be executed.
    :param variables: A dictionary of variables to be passed with the query.
    :return: The result of the query as a string.
    """
    try:
        token, dc = request_wiz_api_token(CLIENT_ID, CLIENT_SECRET)
        HEADERS["Authorization"] = "Bearer " + token
    except requests.exceptions.HTTPError as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Error authenticating to Wiz: {str(e)}")) from e
    except requests.exceptions.ConnectionError as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Network problem: {str(e)}")) from e
    except requests.exceptions.Timeout as e:
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Request timed out: {str(e)}")) from e

    if variables is None:
        variables = {}

    data = {"variables": variables, "query": query}

    try:
        # Uncomment the next first line and comment the line after that
        # to run behind proxies
        # result = requests.post(url=f"https://api.{dc}.app.wiz.io/graphql",
        #                        json=data, headers=HEADERS, proxies=proxyDict, timeout=180)
        result = requests.post(url=f"https://api.{dc}.app.wiz.io/graphql",
                               json=data, headers=HEADERS, timeout=180)

    except requests.exceptions.HTTPError as e:
        print(f"<p>Wiz-API-Error (4xx/5xx): {str(e)}</p>")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"An unexpected error occurred: {str(e)}")) from e

    except requests.exceptions.ConnectionError as e:
        print(f"<p>Network problem (DNS failure, refused connection, etc): {str(e)}</p>")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"An unexpected error occurred: {str(e)}")) from e

    except requests.exceptions.Timeout as e:
        print(f"<p>Request timed out: {str(e)}</p>")
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"An unexpected error occurred: {str(e)}")) from e

    return result.json()

    
sse = SseServerTransport("/messages/")

async def handle_sse(request: Request) -> None:
    _server = mcp._mcp_server
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send,
    ) as (reader, writer):
        await _server.run(reader, writer, _server.create_initialization_options())

app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)