import os
import subprocess
import sys

# List of sensitive keys to migrate
SENSITIVE_KEYS = [
    "DB_USER",
    "DB_PASS",
    "JWT_SECRET_KEY",
    "GROQ_API_KEY",
    "API_NINJAS_KEY",
    "MAIL_PASSWORD",
    "MAIL_USERNAME",
    "MAIL_FROM"
]

PROJECT_ID = "vinsight-ai"

def create_secret(secret_id, value):
    """Creates a secret and adds a new version."""
    print(f"Processing {secret_id}...")
    
    # 1. Create secret (ignore if exists)
    cmd_create = [
        "./google-cloud-sdk/bin/gcloud", "secrets", "create", secret_id,
        f"--project={PROJECT_ID}", "--replication-policy=automatic"
    ]
    # We allow failure here (e.g. if already exists)
    subprocess.run(cmd_create, capture_output=True)
    
    # 2. Add version using safe stdin passing
    cmd_add = [
        "./google-cloud-sdk/bin/gcloud", "secrets", "versions", "add", secret_id,
        f"--project={PROJECT_ID}", "--data-file=-"
    ]
    
    try:
        # Pass value directly to stdin, avoiding shell escaping issues
        result = subprocess.run(
            cmd_add,
            input=value,
            text=True,
            capture_output=True,
            check=True
        )
        print(f"  -> Success: {secret_id} updated.")
        # print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"  -> Failed: {secret_id}")
        print(f"     Error: {e.stderr.strip()}")

def main():
    env_path = os.path.join(os.path.dirname(__file__), '../backend/.env')
    
    if not os.path.exists(env_path):
        print(f"Error: {env_path} not found.")
        sys.exit(1)
        
    print(f"Reading secrets from {env_path}...")
    
    # Read .env file manually to avoid 'source' issues
    secrets = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                secrets[key] = value

    for key in SENSITIVE_KEYS:
        if key in secrets:
            create_secret(key, secrets[key])
        else:
            print(f"Skipping {key} (not found in .env)")

if __name__ == "__main__":
    main()
