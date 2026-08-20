import os
import json
import csv
from datetime import datetime
from azure.identity import EnvironmentCredential
from azure.mgmt.resource.resources import ResourceManagementClient

# Required tags every resource should have
REQUIRED_TAGS = ["owner", "environment", "cost-center"]

def get_client():
    """Authenticate and return an Azure Resource Management client."""
    credential = EnvironmentCredential()
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    return ResourceManagementClient(credential, subscription_id)

def scan_resources(client):
    """Fetch all resources in the subscription."""
    resources = []
    for resource in client.resources.list():
        resources.append({
            "name": resource.name,
            "type": resource.type,
            "resource_group": resource.id.split("/")[4] if "/resourceGroups/" in resource.id else "unknown",
            "location": resource.location,
            "tags": resource.tags or {}
        })
    return resources

def check_compliance(resources):
    """Split resources into compliant and non-compliant based on required tags."""
    compliant = []
    non_compliant = []

    for res in resources:
        missing_tags = [tag for tag in REQUIRED_TAGS if tag not in res["tags"]]
        if missing_tags:
            res["missing_tags"] = missing_tags
            non_compliant.append(res)
        else:
            compliant.append(res)

    return compliant, non_compliant

def save_report(compliant, non_compliant):
    """Save findings to CSV and print a summary."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"compliance_report_{timestamp}.csv"

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Type", "Resource Group", "Location", "Missing Tags"])
        for res in non_compliant:
            writer.writerow([
                res["name"],
                res["type"],
                res["resource_group"],
                res["location"],
                ", ".join(res["missing_tags"])
            ])

    total = len(compliant) + len(non_compliant)
    compliance_pct = (len(compliant) / total * 100) if total > 0 else 100

    print(f"\n=== Tagging Compliance Report ===")
    print(f"Total resources scanned: {total}")
    print(f"Compliant: {len(compliant)}")
    print(f"Non-compliant: {len(non_compliant)}")
    print(f"Compliance rate: {compliance_pct:.1f}%")
    print(f"Detailed report saved to: {filename}\n")

    summary = {
        "timestamp": timestamp,
        "total": total,
        "compliant": len(compliant),
        "non_compliant": len(non_compliant),
        "compliance_pct": round(compliance_pct, 1)
    }
    with open("summary_history.jsonl", "a") as f:
        f.write(json.dumps(summary) + "\n")

    return filename

def main():
    print("Authenticating with Azure...")
    client = get_client()

    print("Scanning resources...")
    resources = scan_resources(client)

    print(f"Found {len(resources)} resources. Checking tags...")
    compliant, non_compliant = check_compliance(resources)

    save_report(compliant, non_compliant)

if __name__ == "__main__":
    main()
