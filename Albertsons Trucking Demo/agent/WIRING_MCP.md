# Wiring the MCP server into the Foundry agent

The agent lives in Foundry resource `RB-FoundryDeployment`, project `AlbertsonsRouting`, agent `AlbertsonsRoutingCopilot`.

The MCP server is deployed at:

```
https://albrouting4yr5k6megl7yk-mcp.purplecliff-a99ba37e.westus2.azurecontainerapps.io/mcp
```

It exposes 8 tools wrapping the routing backend + Cosmos read helpers:
`optimize_from_samples`, `optimize`, `reoptimize`, `validate`, `explain`, `compare`, `list_purchase_orders`, `get_optimization_run`.

## Option 1 — Portal (recommended, no auth juggling)

1. Open https://ai.azure.com/nextgen/r/gnCTC0lmRL2vAZ7x0RgaUQ,RBE-Foundry-RG,,RB-FoundryDeployment,AlbertsonsRouting/home
2. Open the `AlbertsonsRoutingCopilot` agent.
3. In **Tools / Actions**, add **MCP server**:
   - **Server label**: `albertsons-routing-mcp`
   - **Server URL**: `https://albrouting4yr5k6megl7yk-mcp.purplecliff-a99ba37e.westus2.azurecontainerapps.io/mcp`
   - **Authentication**: None (the container app currently has no auth — see hardening below)
   - **Approval**: Never (it's a read/optimization tool)
4. Save the agent.

## Option 2 — CLI

Use the Foundry MCP tooling once you're signed in as `admin@MngEnvMCAP999871.onmicrosoft.com` in the Azure extension auth context:

1. Run `azure_auth-set_auth_context` → `wizard` and pick the `admin@MngEnvMCAP999871.onmicrosoft.com` account / `MCAPS-Ryan-Brown-External` subscription.
2. Then `mcp_foundry_mcp_agent_update` with the `agentDefinition` from `agent/agent_definition.json` (already updated to include the MCP tool entry).

## Hardening (later)

The MCP container app is currently unauthenticated. To lock it down:
- Add API key auth via Container Apps ingress restrictions or an APIM front door, then put the key in Key Vault and reference it in the Foundry connection.
- Or front it with an Entra ID-protected Container App (`enableSystemAssigned`, app role check in middleware).
