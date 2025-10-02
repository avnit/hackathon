"""
# Python 3.9+
pip(3) install requests
"""
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

# Uncomment the following section to define the proxies in your environment,
#   if necessary:
# http_proxy  = "http://"+user+":"+passw+"@x.x.x.x:abcd"
# https_proxy = "https://"+user+":"+passw+"@y.y.y.y:abcd"
# proxyDict = {
#     "http"  : http_proxy,
#     "https" : https_proxy
# }

# The GraphQL query that defines which data you wish to fetch.
QUERY = """
    query IssuesGroupedByValueTable($groupBy: IssuesGroupedByValueField!, $filterBy: IssueFilters, $orderBy: IssueOrder, $groupOrderBy: IssuesGroupedByValueOrder, $first: Int, $after: String, $fetchTotalCount: Boolean = true, $fetchIssues: Boolean!, $fetchSecurityScoreImpact: Boolean = false, $fetchThreatDetectionDetails: Boolean = false, $securityScoreImpactSelection: SecurityScoreImpactSelection, $fetchActorsAndResourcesGraphEntities: Boolean = false, $fetchCloudAccountsAndCloudOrganizations: Boolean = false, $fetchCommentThread: Boolean = false, $fetchThreatCenterActors: Boolean = false, $fetchTdrLogic: Boolean = false, $fetchSecuritySubCategories: Boolean = false, $fetchPrivilegedActionRequests: Boolean = false) {
      issuesGroupedByValue(
        groupBy: $groupBy
        filterBy: $filterBy
        first: $first
        after: $after
        orderBy: $groupOrderBy
      ) {
        nodes {
          id
          issues(first: 5, orderBy: $orderBy) {
            nodes @include(if: $fetchIssues) {
              id
              type
              resolvedAt
              resolutionReason
              ...ResolvedByUser
              sourceRules {
                ...SourceRuleFields
                securitySubCategories @include(if: $fetchSecuritySubCategories) {
                  id
                  title
                  category {
                    id
                    name
                    framework {
                      id
                      name
                      enabled
                    }
                  }
                }
              }
              assignee {
                ...IssueAssignee
              }
              createdAt
              updatedAt
              resolvedAt
              dueAt
              rejectionExpiredAt
              projects {
                id
                name
                slug
                isFolder
                businessUnit
                riskProfile {
                  businessImpact
                }
              }
              status
              severity
              resolutionReason
              entitySnapshot {
                id
                type
                status
                name
                cloudPlatform
                subscriptionName
                subscriptionId
                subscriptionExternalId
                region
                nativeType
                kubernetesClusterId
                kubernetesClusterName
                kubernetesNamespaceName
                tags
                externalId
              }
              notes {
                id
                text
              }
              cloudAccounts @include(if: $fetchCloudAccountsAndCloudOrganizations) {
                id
                name
                externalId
                cloudProvider
              }
              cloudOrganizations @include(if: $fetchCloudAccountsAndCloudOrganizations) {
                id
                name
                externalId
                cloudProvider
              }
              threatDetectionDetails @include(if: $fetchThreatDetectionDetails) {
                ...ThreatDetectionDetailsActorsResources
                ...ThreatDetectionDetailsMainDetection
                detections(first: 0) {
                  totalCount
                }
                eventOrigin
              }
              threatCenterActors @include(if: $fetchThreatCenterActors) {
                id
                name
                type
              }
              serviceTickets {
                id
                externalId
                name
                url
              }
              commentThread @include(if: $fetchCommentThread) {
                id
                hasComments
              }
              privilegedActionRequests @include(if: $fetchPrivilegedActionRequests) {
                ...PendingIgnoreRequest
              }
            }
            totalCount
            criticalSeverityCount
            highSeverityCount
            mediumSeverityCount
            lowSeverityCount
            informationalSeverityCount
            pageInfo {
              hasNextPage
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
        totalCount @include(if: $fetchTotalCount)
      }
    }
    
        fragment ResolvedByUser on Issue {
      resolvedBy {
        user {
          id
          email
          name
        }
      }
    }
    

        fragment SourceRuleFields on IssueSourceRule {
      ... on CloudConfigurationRule {
        id
        tags {
          key
          value
        }
        builtin
        createdBy {
          name
        }
        name
        description
        subjectEntityType
        hasAutoRemediation
        cloudProvider
        securityScoreImpact(selection: $securityScoreImpactSelection) @include(if: $fetchSecurityScoreImpact)
        risks
        threats
        control {
          id
          resolutionRecommendation
        }
      }
      ... on CloudEventRule {
        id
        name
        cloudEventRuleType: type
        description
        ruleSeverity: severity
        builtin
        createdBy {
          name
        }
        generateIssues
        generateFindings
        enabled
        sourceType
        ...CloudEventRuleLogicFields @include(if: $fetchTdrLogic)
        securityScoreImpact(selection: $securityScoreImpactSelection) @include(if: $fetchSecurityScoreImpact)
        risks
        threats
        ...CloudEventRuleForensicsPolicyFields
      }
      ... on Control {
        id
        tagsV2 {
          key
          value
        }
        name
        query
        type
        enabled
        enabledForHBI
        enabledForLBI
        enabledForMBI
        enabledForUnattributed
        builtin
        severity
        createdBy {
          id
          name
          email
        }
        sourceCloudConfigurationRule {
          id
          name
        }
        serviceTickets {
          ...ControlServiceTicket
        }
        resolutionRecommendation
        description
        securityScoreImpact(selection: $securityScoreImpactSelection) @include(if: $fetchSecurityScoreImpact)
        risks
        threats
      }
    }
    

        fragment CloudEventRuleLogicFields on CloudEventRule {
      params {
        ...CloudEventRuleParamsLogicFields
        ...CloudEventInlineRuleParamsLogicFields
        ...CloudEventSensorRuleLogicParams
      }
    }
    

        fragment CloudEventRuleParamsLogicFields on CorrelationCloudEventRuleParams {
      securityGraphContext {
        description
        inUse
      }
      detectionThresholds {
        inUse
      }
      behavioralBaselines {
        id
        builtInId
        title
        description
      }
      threatIntelligenceInformation {
        ...ThreatIntelligenceInformationFields
      }
    }
    

        fragment ThreatIntelligenceInformationFields on CloudEventRuleThreatIntelligenceInformation {
      __typename
      description
    }
    

        fragment CloudEventInlineRuleParamsLogicFields on CloudEventRuleParams {
      securityGraphContext {
        description
        inUse
      }
      threatIntelligenceInformation {
        ...ThreatIntelligenceInformationFields
      }
    }
    

        fragment CloudEventSensorRuleLogicParams on WorkloadRuntimeRuleParams {
      threatIntelligenceInformation {
        ...ThreatIntelligenceInformationFields
      }
    }
    

        fragment CloudEventRuleForensicsPolicyFields on CloudEventRule {
      sensorForensicsCollectionSupported
      sensorForensicsCollectionPolicy {
        id
      }
    }
    

        fragment ControlServiceTicket on ServiceTicket {
      id
      externalId
      name
      url
      project {
        id
        name
      }
      integration {
        id
        type
        name
        typeConfiguration {
          type
          iconUrl
        }
      }
    }
    

        fragment IssueAssignee on Identity {
      id
      name
      primaryEmail
    }
    

        fragment ThreatDetectionDetailsActorsResources on ThreatDetectionIssueDetails {
      actorsMaxCountReached
      actorsTotalCount
      actors {
        id
        name
        externalId
        providerUniqueId
        type
        nativeType
        graphEntity @include(if: $fetchActorsAndResourcesGraphEntities) {
          id
          deletedAt
          type
          name
          properties
        }
      }
      resourcesTotalCount
      resourcesMaxCountReached
      resources {
        id
        name
        externalId
        providerUniqueId
        type
        nativeType
        graphEntity @include(if: $fetchActorsAndResourcesGraphEntities) {
          id
          type
          deletedAt
          name
          properties
        }
      }
    }
    

        fragment ThreatDetectionDetailsMainDetection on ThreatDetectionIssueDetails {
      mainDetection {
        id
        startedAt
        severity
        description(format: MARKDOWN)
        ruleMatch {
          rule {
            id
            name
            origins
          }
        }
      }
    }
    

        fragment PendingIgnoreRequest on PrivilegedActionRequest {
      id
      type
      status
    }
"""

# The variables sent along with the above query
VARIABLES = {
  "fetchTotalCount": True,
  "fetchSecurityScoreImpact": True,
  "fetchThreatDetectionDetails": False,
  "fetchActorsAndResourcesGraphEntities": False,
  "fetchCloudAccountsAndCloudOrganizations": False,
  "fetchCommentThread": True,
  "fetchThreatCenterActors": False,
  "fetchTdrLogic": False,
  "fetchSecuritySubCategories": False,
  "fetchPrivilegedActionRequests": False,
  "first": 20,
  "fetchIssues": True,
  "filterBy": {
    "status": [
      "OPEN",
      "IN_PROGRESS"
    ],
    "relatedEntity": {},
    "frameworkCategory": [
      "wct-id-422"
    ],
    "sourceRule": {},
    "type": [
      "CLOUD_CONFIGURATION",
      "TOXIC_COMBINATION"
    ]
  },
  "groupBy": "SOURCE_RULE",
  "groupOrderBy": {
    "field": "SEVERITY",
    "direction": "DESC"
  },
  "orderBy": {
    "direction": "DESC",
    "field": "SEVERITY"
  },
  "securityScoreImpactSelection": {}
}

mcp = FastMCP()

@mcp.tool()
def query_wiz_api(query, variables, dc):
    """Query Wiz API for the given query data schema"""

    data = {"variables": variables, "query": query}

    token_dc = request_wiz_api_token(CLIENT_ID, CLIENT_SECRET)
    if isinstance(token_dc, Exception):
        raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Error authenticating to Wiz: {str(token_dc)}"))
    token, dc = token_dc
    HEADERS["Authorization"] = "Bearer " + token
    try:
        # Uncomment the next first line and comment the line after that
        # to run behind proxies
        # result = requests.post(url=f"https://api.{dc}.app.wiz.io/graphql",
        #                        json=data, headers=HEADERS, proxies=proxyDict, timeout=180)
        result = requests.post(url=f"https://api.{dc}.app.wiz.io/graphql",
                               json=data, headers=HEADERS, timeout=180)

    except requests.exceptions.HTTPError as e:
        print(f"<p>Wiz-API-Error (4xx/5xx): {str(e)}</p>")
        return e

    except requests.exceptions.ConnectionError as e:
        print(f"<p>Network problem (DNS failure, refused connection, etc): {str(e)}</p>")
        return e

    except requests.exceptions.Timeout as e:
        print(f"<p>Request timed out: {str(e)}</p>")
        return e

    return result.json()


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

    except requests.exceptions.HTTPError as e:
        print(f"<p>Error authenticating to Wiz (4xx/5xx): {str(e)}</p>")
        return e

    except requests.exceptions.ConnectionError as e:
        print(f"<p>Network problem (DNS failure, refused connection, etc): {str(e)}</p>")
        return e

    except requests.exceptions.Timeout as e:
        print(f"<p>Request timed out: {str(e)}</p>")
        return e

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




    # The above code lists the first <x> items.
    # If paginating on a Graph Query,
    #   then use <'quick': False> in the query variables.
    # Uncomment the following section to paginate over all the results:
    # pageInfo = result['data']['issuesGroupedByValue']['pageInfo']
    # while (pageInfo['hasNextPage']):
    #     # fetch next page
    #     VARIABLES['after'] = pageInfo['endCursor']
    #     result = query_wiz_api(QUERY, VARIABLES, dc)
    #     print(result)
    #     pageInfo = result['data']['issuesGroupedByValue']['pageInfo']

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

if __name__ == '__main__':
    uvicorn.run(app, host="localhost", port=8001)

