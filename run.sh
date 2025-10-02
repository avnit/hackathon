export GOOGLE_CLOUD_PROJECT=atus-security-dev
export GOOGLE_CLOUD_LOCATION=us-central1
export AIP_ENDPOINT_ID=test-poc-template
export GOOGLE_GENAI_USE_VERTEXAI=true
adk deploy cloud_run --project atus-security-dev --region us-central1 --service_name wiz-search-agent  ./ai-agent
