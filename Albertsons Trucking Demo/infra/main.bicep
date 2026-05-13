// Albertsons Truck Routing — minimal demo infrastructure.
//
// Deploys:
//  * Log Analytics + App Insights
//  * Azure Container Registry (for the backend image)
//  * Container Apps environment + Container App (backend)
//  * Storage Account + Blob container (raw uploads)
//  * Key Vault (Azure Maps key + AOAI key)
//  * Static Web App (frontend)
//  * Azure Maps account (for truck-routed distances)
//  * Optional: Azure OpenAI (gpt-4o) — set deployOpenAI = true.
//
// Out of scope for this POC: AI Foundry hub, Cosmos DB, Front Door.

@minLength(3)
@maxLength(11)
param namePrefix string = 'albrouting'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Tags applied to all resources.')
param tags object = {
  workload: 'albertsons-routing-demo'
  environment: 'demo'
}

@description('Set true to provision Azure OpenAI (gpt-4o). Subscription must be enabled.')
param deployOpenAI bool = false

@description('Container image for backend, e.g. <acr-login-server>/backend:latest. Leave empty to deploy a placeholder image.')
param backendImage string = ''

var uniqueSuffix = uniqueString(resourceGroup().id)
var resName = toLower('${namePrefix}${uniqueSuffix}')

// ------------------ Observability ------------------
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${resName}-law'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resName}-appi'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
  }
}

// ------------------ ACR ------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${resName}acr'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// ------------------ Storage ------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${resName}sa'
  location: location
  tags: tags
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource blobsvc 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource uploadsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobsvc
  name: 'uploads'
}

// ------------------ Key Vault ------------------
resource kv 'Microsoft.KeyVault/vaults@2024-04-01-preview' = {
  name: '${resName}-kv'
  location: location
  tags: tags
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
  }
}

// ------------------ Azure Maps ------------------
resource maps 'Microsoft.Maps/accounts@2024-01-01-preview' = {
  name: '${resName}-maps'
  location: 'global'
  tags: tags
  sku: { name: 'G2' }
  kind: 'Gen2'
  properties: {
    disableLocalAuth: false
  }
}

// ------------------ Container Apps env ------------------
resource cae 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${resName}-cae'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

resource backend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${resName}-backend'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: empty(backendImage) ? [] : [
        {
          server: '${acr.name}.azurecr.io'
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-pwd'
        }
      ]
      secrets: empty(backendImage) ? [] : [
        {
          name: 'acr-pwd'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: empty(backendImage) ? 'mcr.microsoft.com/azuredocs/aci-helloworld:latest' : backendImage
          resources: { cpu: 1, memory: '2Gi' }
          env: [
            { name: 'APPINSIGHTS_CONNECTION_STRING', value: appi.properties.ConnectionString }
            { name: 'AZURE_MAPS_KEY', value: listKeys(maps.id, '2024-01-01-preview').primaryKey }
            { name: 'CORS_ORIGINS', value: 'https://${swa.properties.defaultHostname}' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ------------------ Static Web App (frontend) ------------------
resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${resName}-swa'
  location: location
  tags: tags
  sku: { name: 'Free', tier: 'Free' }
  properties: {
    repositoryUrl: ''
    branch: ''
    buildProperties: {
      appLocation: 'frontend'
      outputLocation: 'dist'
    }
  }
}

// ------------------ Optional: Azure OpenAI ------------------
resource aoai 'Microsoft.CognitiveServices/accounts@2024-10-01' = if (deployOpenAI) {
  name: '${resName}-aoai'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: '${resName}-aoai'
    publicNetworkAccess: 'Enabled'
  }
}

resource gpt4o 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if (deployOpenAI) {
  parent: aoai
  name: 'gpt-4o'
  sku: { name: 'GlobalStandard', capacity: 50 }
  properties: {
    model: { format: 'OpenAI', name: 'gpt-4o', version: '2024-08-06' }
  }
}

output backendUrl string = 'https://${backend.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${swa.properties.defaultHostname}'
output appInsightsName string = appi.name
output acrLoginServer string = acr.properties.loginServer
output azureMapsAccount string = maps.name
output keyVaultName string = kv.name
