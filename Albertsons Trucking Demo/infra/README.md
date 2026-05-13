# Infra (`infra/main.bicep`)

Provisions the demo Azure footprint:

| Resource | Purpose |
| --- | --- |
| Log Analytics + App Insights | Telemetry for backend |
| Azure Container Registry | Backend image hosting |
| Container Apps env + app | Hosts the FastAPI backend |
| Storage Account + `uploads` container | Raw file uploads |
| Key Vault | Secret storage (Azure Maps key, AOAI key) |
| Azure Maps (Gen2 G2) | Truck routing distance matrix |
| Static Web App (Free) | Hosts the React frontend |
| Azure OpenAI (optional) | gpt-4o deployment for the agent |

## Deploy

```powershell
az group create -n rg-albrouting-demo -l westus3

az deployment group create `
  -g rg-albrouting-demo `
  -f infra/main.bicep `
  -p infra/parameters.json
```

To enable AOAI: `-p deployOpenAI=true`.

After deploying, push the backend image:

```powershell
az acr login -n <acrName>
docker build -t <acrName>.azurecr.io/backend:latest backend
docker push <acrName>.azurecr.io/backend:latest

az containerapp update -n <albrouting...-backend> -g rg-albrouting-demo `
  --image <acrName>.azurecr.io/backend:latest
```

Then connect the SWA to your GitHub repo via the portal (or `az staticwebapp` commands) so the React build pipeline picks up `frontend/`.
