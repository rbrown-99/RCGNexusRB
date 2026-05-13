// Albertsons Truck Routing — minimal demo infrastructure.
//
// Deploys:
//  * Log Analytics + App Insights
//  * Azure Container Registry (for the backend + MCP server images)
//  * Container Apps environment + 2 Container Apps (backend, mcp-server)
//  * Storage Account + Blob container (raw uploads)
//  * Cosmos DB (serverless, SQL API) — purchase orders, optimization runs, sessions
//  * Key Vault (Azure Maps key + AOAI key)
//  * Static Web App (frontend)
//  * Azure Maps account (for truck-routed distances)
//  * Optional: Azure OpenAI (gpt-4o) — set deployOpenAI = true.
//
// Out of scope for this POC: AI Foundry hub (separate RG), Front Door.

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

@description('Container image for MCP server. Leave empty to deploy a placeholder image.')
param mcpImage string = ''

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
  name: '${take(resName, 22)}sa'
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
  name: '${take(resName, 21)}-kv'
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

// ------------------ Cosmos DB (serverless, SQL API) ------------------
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${resName}-cosmos'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      { name: 'EnableServerless' }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
  }
}

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'routing'
  properties: {
    resource: { id: 'routing' }
  }
}

var cosmosContainers = [
  { name: 'purchase_orders',   pk: '/store_code' }
  { name: 'optimization_runs', pk: '/session_id' }
  { name: 'sessions',          pk: '/session_id' }
]

resource cosmosColls 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = [for c in cosmosContainers: {
  parent: cosmosDb
  name: c.name
  properties: {
    resource: {
      id: c.name
      partitionKey: {
        paths: [ c.pk ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [ { path: '/*' } ]
        excludedPaths: [ { path: '/"_etag"/?' } ]
      }
    }
  }
}]

// Built-in Cosmos DB Data Contributor role definition (well-known ID 00000000-0000-0000-0000-000000000002).
var cosmosDataContribRoleId = '00000000-0000-0000-0000-000000000002'

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
            { name: 'CORS_ORIGINS', value: 'https://${swa.properties.defaultHostname},http://localhost:5173,http://localhost:4173' }
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DATABASE', value: cosmosDb.name }
            { name: 'AZURE_CLIENT_ID', value: '' } // system-assigned MI — leave blank, DefaultAzureCredential picks it up
          ]
        }
      ]
      scale: { minReplicas: 0, maxReplicas: 3 }
    }
  }
}

// Grant the backend Container App's system-assigned MI data-plane access to Cosmos.
resource backendCosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, backend.id, 'data-contrib')
  properties: {
    principalId: backend.identity.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContribRoleId}'
    scope: cosmos.id
  }
}

// ------------------ MCP Server (Container App) ------------------
resource mcp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${resName}-mcp'
  location: location
  tags: tags
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
      registries: empty(mcpImage) ? [] : [
        {
          server: '${acr.name}.azurecr.io'
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-pwd'
        }
      ]
      secrets: empty(mcpImage) ? [] : [
        {
          name: 'acr-pwd'
          value: acr.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp'
          image: empty(mcpImage) ? 'mcr.microsoft.com/azuredocs/aci-helloworld:latest' : mcpImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'APPINSIGHTS_CONNECTION_STRING', value: appi.properties.ConnectionString }
            { name: 'BACKEND_URL', value: 'https://${backend.properties.configuration.ingress.fqdn}' }
            { name: 'COSMOS_ENDPOINT', value: cosmos.properties.documentEndpoint }
            { name: 'COSMOS_DATABASE', value: cosmosDb.name }
          ]
        }
      ]
      scale: { minReplicas: 0, maxReplicas: 2 }
    }
  }
}

resource mcpCosmosRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmos
  name: guid(cosmos.id, mcp.id, 'data-contrib')
  properties: {
    principalId: mcp.identity.principalId
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/${cosmosDataContribRoleId}'
    scope: cosmos.id
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
output mcpUrl string = 'https://${mcp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${swa.properties.defaultHostname}'
output appInsightsName string = appi.name
output acrLoginServer string = acr.properties.loginServer
output azureMapsAccount string = maps.name
output keyVaultName string = kv.name
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosDatabase string = cosmosDb.name
output swaName string = swa.name
output backendAppName string = backend.name
output mcpAppName string = mcp.name
output acrName string = acr.name
