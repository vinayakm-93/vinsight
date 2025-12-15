import os

ENV_PATH = "backend/.env"

def update_env(key, value):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r") as f:
            lines = f.readlines()

    new_lines = []
    found = False
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        # Ensure newline before appending if file doesn't end with one
        if new_lines and not new_lines[-1].endswith('\n'):
             new_lines[-1] += '\n'
        new_lines.append(f"{key}={value}\n")

    with open(ENV_PATH, "w") as f:
        f.writelines(new_lines)
    print(f"Updated {key}")

if __name__ == "__main__":
    print("--- Setup Mail Environment ---")
    print("Security Note: This script saves your credentials to .env (which is gitignored).")
    
    email = input("Enter Gmail Address: ").strip()
    password = input("Enter App Password (spaces removed): ").strip()
    
    if email and password:
        update_env("MAIL_USERNAME", email)
        update_env("MAIL_PASSWORD", password.replace(" ", ""))
        update_env("MAIL_FROM", email)
        update_env("MAIL_PORT", "587")
        update_env("MAIL_SERVER", "smtp.gmail.com")
        print("Success: Credentials updated in .env")
    else:
        print("Skipped: Missing input.")
    
    print("Environment setup complete.")
