
import os
import argparse
from google.cloud import run_v2
from google.cloud.devtools import cloudbuild_v1
from google.iam.v1 import iam_policy_pb2
from google.iam.v1 import policy_pb2
def build_and_push_image(project_id, location, repository, image_name, tag="latest"):
    """Builds a Docker image using Google Cloud Build and pushes it to GCR."""
    client = cloudbuild_v1.CloudBuildClient()

    build = cloudbuild_v1.Build()
    build.source = cloudbuild_v1.Source(storage_source=None, repo_source=None) # Should be set to the directory of the Dockerfile
    build.steps = [
        cloudbuild_v1.BuildStep(
            name="gcr.io/cloud-builders/docker",
            args=["build", "-t", f"{location}-docker.pkg.dev/{project_id}/{repository}/{image_name}:{tag}", "."]
        )
    ]
    build.images = [f"{location}-docker.pkg.dev/{project_id}/{repository}/{image_name}:{tag}"]

    operation = client.create_build(project_id=project_id, build=build)
    print("Waiting for Cloud Build to complete...")
    result = operation.result()
    print(f"Image built and pushed: {build.images[0]}")
    return build.images[0]

def deploy_to_cloud_run(project_id, location, service_name, image_uri):
    """Deploys a container image to Cloud Run."""
    client = run_v2.ServicesClient()
 
    service = run_v2.Service(
        template=run_v2.RevisionTemplate(
            containers=[run_v2.Container(image=image_uri)]
        )
    )

    operation = client.create_service(
        parent=f"projects/{project_id}/locations/{location}",
        service_id=service_name,
        service=service,
    )
    print(f"Deploying {service_name} to Cloud Run...")
    response = operation.result()
    # Print the full response to debug available attributes
    print(f"Service deployed response: {response}")
    # Try to get the service URL from known attributes
    service_url = getattr(response, "uri", None)
    if not service_url and hasattr(response, "status") and getattr(response.status, "url", None) is not None:
        service_url = getattr(response.status, "url", None)
    if service_url:
        print(f"Service deployed: {service_url}")
        return service_url
    else:
        print("Could not find service URL in response.")
        return None

# def make_service_public(project_id, location, service_name):
#     """Makes a Cloud Run service publicly accessible."""
#     client = run_v2.ServicesClient()
#     service_path = f"projects/{project_id}/locations/{location}/services/{service_name}"
#     policy = policy_pb2.Policy(
#         bindings=[
#             policy_pb2.Binding(
#                 role="roles/run.invoker",
#                 members=["allUsers"],
#             )
#         ]
#     )
    
#     request = iam_policy_pb2.SetIamPolicyRequest(resource=service_path, policy=policy)
#     client.set_iam_policy(request=request)
#     print(f"Service {service_name} is now public.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True, help="GCP project ID.")
    parser.add_argument("--location", default="us-central1", help="GCP location.")
    parser.add_argument("--repository", required=True, help="GCR repository name.")
    parser.add_argument("--image-name", default="wiz-mcp-server", help="Name of the Docker image.")
    parser.add_argument("--service-name", default="wiz-mcp-server", help="Name of the Cloud Run service.")
    args = parser.parse_args()

    # This script assumes it's run from the root of the wiz-mcp directory
    # and that the Dockerfile is in the same directory.
    # A more robust solution would be to specify the path to the Dockerfile.
    
    # To run this script, you need to have the Google Cloud SDK installed and authenticated.
    # You also need to enable the Cloud Build and Cloud Run APIs in your GCP project.

    image_uri = build_and_push_image(args.project_id, args.location, args.repository, args.image_name)
    service_uri = deploy_to_cloud_run(args.project_id, args.location, args.service_name, image_uri)
    # make_service_public(args.project_id, args.location, args.service_name)

    print(f"Deployment complete. The wiz-mcp-server is running at: {service_uri}")
    print("You can now update the WIZ_MCP_SERVER_URL environment variable in the llm-auditor to this URL.")
