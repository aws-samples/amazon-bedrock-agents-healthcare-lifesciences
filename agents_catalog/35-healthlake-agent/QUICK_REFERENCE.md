# HealthLake Agent - Quick Reference Card

## 🚀 Quick Start (3 Steps)

### 1. Run Integration Script

**Windows:**
```powershell
.\agents_catalog\35-healthlake-agent\scripts\integrate_with_template.ps1
```

**Linux/Mac:**
```bash
chmod +x agents_catalog/35-healthlake-agent/scripts/integrate_with_template.sh
./agents_catalog/35-healthlake-agent/scripts/integrate_with_template.sh
```

### 2. Update Agent Code

Edit `agentcore_template/agent/agent_config/agent_task.py`:

```python
# Add import at top
from .tools.healthlake_tools import HEALTHLAKE_TOOLS

# Update agent creation (around line 30)
agent = TemplateAgent(
    bearer_token=gateway_access_token,
    memory_hook=memory_hook,
    tools=HEALTHLAKE_TOOLS,  # Add this line
)
```

### 3. Deploy & Test

```bash
cd agentcore_template
agentcore configure --entrypoint main.py -rf agent/requirements.txt -er <role-arn> --name myapp-healthlake-agent
rm .agentcore.yaml
agentcore launch
agentcore invoke '{"prompt": "What is the HealthLake datastore information?"}' --agent myapp-healthlake-agent
```

## 🛠️ Available Tools

| Tool | Description | Example Query |
|------|-------------|---------------|
| `Get_HealthLake_Datastore_Info` | Get datastore metadata | "What is the datastore info?" |
| `Search_FHIR_Resources` | Search for FHIR resources | "Find patients named Smith" |
| `Read_FHIR_Resource` | Get complete resource details | "Read patient ID abc123" |
| `Get_Patient_Everything` | Get all patient resources | "Get all records for patient abc123" |

## 📝 Common FHIR Searches

### Patient Search
```
"Search for patients with family name Smith"
"Find patients born after 1990-01-01"
"Search for patients with given name John"
```

### Observation Search
```
"Find all observations for patient ID abc123"
"Search for blood pressure observations"
"Find observations with code 12345"
```

### Condition Search
```
"Search for conditions for patient ID abc123"
"Find active conditions with code diabetes"
"Search for resolved conditions"
```

### Medication Search
```
"Find medications for patient ID abc123"
"Search for active medication requests"
```

## 🔧 Configuration

### SSM Parameters
```bash
# HealthLake datastore ID
/app/myapp/healthlake/datastore_id

# Other template parameters
/app/myapp/agentcore/runtime_iam_role
/app/myapp/agentcore/gateway_url
/app/myapp/agentcore/memory_id
```

### IAM Permissions Required
```json
{
  "Effect": "Allow",
  "Action": [
    "healthlake:DescribeFHIRDatastore",
    "healthlake:ReadResource",
    "healthlake:SearchWithGet",
    "healthlake:SearchWithPost"
  ],
  "Resource": "arn:aws:healthlake:*:*:datastore/fhir/*"
}
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Datastore ID not configured" | Create SSM parameter: `/app/myapp/healthlake/datastore_id` |
| "Access Denied" | Attach HealthLake IAM policy to runtime role |
| "Tools not available" | Import `HEALTHLAKE_TOOLS` in `agent_task.py` |
| "Invalid search parameters" | Check FHIR parameter names (e.g., "family" not "lastName") |

## 📚 FHIR Search Parameters

### Patient
- `family` - Last name
- `given` - First name
- `birthdate` - Date of birth (YYYY-MM-DD)
- `gender` - Gender (male, female, other, unknown)
- `identifier` - Patient identifier

### Observation
- `patient` - Patient ID
- `code` - Observation code
- `date` - Observation date
- `category` - Observation category

### Condition
- `patient` - Patient ID
- `code` - Condition code
- `clinical-status` - Status (active, inactive, resolved)
- `onset-date` - Onset date

## 🔗 Documentation Links

- **Quick Start**: `AGENTCORE_TEMPLATE_README.md`
- **Detailed Guide**: `INTEGRATION_GUIDE.md`
- **Summary**: `HEALTHLAKE_AGENT_INTEGRATION_SUMMARY.md`
- **Template Docs**: `agentcore_template/README.md`

## 💡 Pro Tips

1. **Use Search Before Read**: Search to find IDs, then use Read for details
2. **Limit Results**: Use `count` parameter to limit search results
3. **Filter Early**: Use search parameters to reduce data transfer
4. **Cache Results**: Store frequently accessed resources
5. **Monitor Costs**: Check CloudWatch metrics for usage patterns

## 🎯 Example Workflows

### Find Patient and Get Records
```
1. "Search for patients with family name Smith"
2. "Read patient resource with ID abc123"
3. "Get all records for patient ID abc123"
```

### Search Observations
```
1. "Find all observations for patient ID abc123"
2. "Read observation resource with ID xyz789"
```

### Check Conditions
```
1. "Search for conditions for patient ID abc123"
2. "Read condition resource with ID def456"
```

## 📊 Cost Estimate

| Service | Monthly Cost (1,000 queries) |
|---------|------------------------------|
| AgentCore Runtime | ~$0.02 |
| Memory (STM) | ~$0.03 |
| CloudWatch Logs | ~$2.50 |
| Bedrock (Claude) | ~$27.50 |
| HealthLake | Pay per request |
| **Total** | **~$30-40** |

## 🔒 Security Checklist

- ✅ Least privilege IAM permissions
- ✅ Encryption at rest and in transit
- ✅ CloudTrail audit logging enabled
- ✅ Role-based access control implemented
- ✅ HIPAA compliance guidelines followed

## 🆘 Support

- **Template Issues**: See `agentcore_template/README.md`
- **HealthLake Issues**: See `agents_catalog/35-healthlake-agent/README.md`
- **AWS Support**: Contact AWS Support
- **FHIR Spec**: https://hl7.org/fhir/R4/

---

**Last Updated**: 2024
**Version**: 1.0.0
