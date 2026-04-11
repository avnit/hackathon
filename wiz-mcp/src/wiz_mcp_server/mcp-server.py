# wiz_mcp_server.py
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from typing import Optional
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import List, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from wiz_mcp_server.auth.auth import authenticate
from wiz_mcp_server.utils.context import WizContext
from wiz_mcp_server.utils.logger import get_logger



load_dotenv()
 
app = FastAPI(title="Wiz MCP Server")
 
# ---- 1. Wiz API Setup ----
WIZ_CLIENT_ID = os.getenv("WIZ_CLIENT_ID")
WIZ_CLIENT_SECRET = os.getenv("WIZ_CLIENT_SECRET")
WIZ_API_URL = os.getenv("WIZ_API_URL", "https://api.us1.app.wiz.io/graphql")
 
ACCESS_TOKEN = None
 
async def get_wiz_token():
    global ACCESS_TOKEN
    if ACCESS_TOKEN:
        return ACCESS_TOKEN
 
    token_url = WIZ_API_URL.replace("/graphql", "/oauth/token")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": WIZ_CLIENT_ID,
                "client_secret": WIZ_CLIENT_SECRET,
                "audience": "wiz-api"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        ACCESS_TOKEN = data["access_token"]
        return ACCESS_TOKEN
async def wiz_query(query: str, variables: Optional[dict] = None):
    token = await get_wiz_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            WIZ_API_URL,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
        return resp.json()
        return resp.json()
 
# ---- 2. GraphQL Queries ----
WIZ_QUERY_ISSUE = """
query GetIssue($id: ID!) {
  issue(id: $id) {
    id
    severity
    status
    entity {
      id
      name
      type
    }
    control {
      id
      name
      remediation
    }
  }
}
"""
 
# ---- 3. Terraform Generator (simplified stub) ----
async def terraform_from_remediation(remediation_text: str, entity: dict):
    """
    Very simple generator – in production, you would call Gemini here
    to parse Wiz remediation text into structured Terraform HCL.
    For now, we map common cases.
    """
    if not remediation_text:
        return "# No remediation available"
 
    resource_type = entity.get("type", "GENERIC_RESOURCE")
 
    if "bucket" in remediation_text.lower():
        return f"""
resource "google_storage_bucket" "{entity.get("name", "secure_bucket")}" {{
  name     = "{entity.get("name", "secure-bucket")}"
  location = "US"
  encryption {{
    default_kms_key_name = "projects/PROJECT_ID/locations/us/keyRings/my-key-ring/cryptoKeys/my-key"
  }}
}}
"""
    elif "iam" in remediation_text.lower():
        return f"""
resource "google_project_iam_binding" "{entity.get("name", "iam_binding")}" {{
  project = "{entity.get("id", "my-project")}"
  role    = "roles/viewer"
 
  members = [
    "user:secure@example.com",
  ]
}}
"""
    else:
        return f"# TODO: Convert remediation into Terraform\n# Original guidance:\n# {remediation_text}"
 
# ---- 4. Handlers ----
async def handle_generate_remediation(params: dict):
    issue_id = params.get("issueId")
    if not issue_id:
        return {"error": "Missing issueId parameter"}
 
    result = await wiz_query(WIZ_QUERY_ISSUE, {"id": issue_id})
    issue = result.get("data", {}).get("issue")
 
    if not issue:
        return {"error": f"Issue {issue_id} not found in Wiz"}
 
    remediation_text = issue["control"]["remediation"] if issue.get("control") else None
    terraform_snippet = await terraform_from_remediation(remediation_text, issue["entity"])
 
    return {
        "issueId": issue["id"],
        "severity": issue["severity"],
        "status": issue["status"],
        "resource": issue["entity"],
        "control": {
            "id": issue["control"]["id"] if issue.get("control") else None,
            "name": issue["control"]["name"] if issue.get("control") else None,
            "remediation": remediation_text or "No remediation provided by Wiz"
        },
        "terraform": terraform_snippet
    }
 
# ---- 5. Dispatcher ----
METHOD_HANDLERS = {
    "generate_remediation": handle_generate_remediation,
}
 
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    try:
        payload = await request.json()
        method = payload.get("method")
        params = payload.get("params", {})
 
        if method not in METHOD_HANDLERS:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": payload.get("id"),
                    "error": {"code": -32601, "message": f"Method '{method}' not found"}
                },
                status_code=400
            )
 
        result = await METHOD_HANDLERS[method](params)
 
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": payload.get("id"),
                "result": result
            }
        )
    except Exception as e:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            },
            status_code=500
        )

def load_environment(env_file_path: Optional[str] = None):
    """
    Load environment variables from a .env file if it exists.

    Args:
        env_file_path: Optional path to a .env file. If not provided, defaults to '.env' in the current directory.
    """
    important_vars = ["WIZ_CLIENT_ID", "WIZ_CLIENT_SECRET", "WIZ_API_URL", "WIZ_ENV"]
    initial_vars = {var: os.environ.get(var) for var in important_vars}

    if env_file_path and os.path.isfile(env_file_path):
        dotenv_path = env_file_path
    else:
        default_path = os.path.join(os.getcwd(), ".env")
        if os.path.isfile(default_path):
            dotenv_path = default_path
        else:
            logger.info("No .env file found")
            dotenv_path = None

    # Load the .env file if found
    if dotenv_path:
        logger.info(f"Loading environment variables from: {dotenv_path}")
        load_dotenv(dotenv_path)

        # Log which variables were loaded
        loaded = [var for var in important_vars
                  if os.environ.get(var) and initial_vars[var] != os.environ.get(var)]
        if loaded:
            logger.info(f"Loaded variables: {', '.join(loaded)}")

    # Log the current WIZ_ENV value
    logger.info(f"Using Wiz environment: {os.environ.get('WIZ_ENV', 'app')}")


_env_loaded = False
SERVER_NAME = "Wiz MCP Server"
logger = get_logger(SERVER_NAME)
@asynccontextmanager
def create_server(env_file_path=None) -> FastMCP:
    """
    Create a configured FastMCP server instance for the Wiz API.

    This function creates and configures a FastMCP server with the appropriate
    lifespan context manager and registers all available Wiz API tools.

    Args:
        env_file_path: Optional path to a .env file containing environment variables

    Returns:
        FastMCP: Configured FastMCP server instance ready to be run
    """
    global server, _env_loaded

    # Only load environment if it hasn't been loaded yet or if a specific path is provided
    if not _env_loaded or env_file_path:
        load_environment(env_file_path)
        _env_loaded = True

    # Create the server instance
    mcp = FastMCP(
        SERVER_NAME,
        lifespan=wiz_lifespan,
    )

    # Update the module-level server variable
    server = mcp

    return mcp


# Initialize the server with default settings
# This is used when the module is imported directly
server = create_server()

# Entry point for direct execution
if __name__ == "__main__":
    from wiz_mcp_server.cli import main

    main()