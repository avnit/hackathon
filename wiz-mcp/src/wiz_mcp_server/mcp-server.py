# wiz_mcp_server.py
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
 
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
 
async def wiz_query(query: str, variables: dict = None):
    token = await get_wiz_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            WIZ_API_URL,
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": f"Bearer {token}"}
        )
        resp.raise_for_status()
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