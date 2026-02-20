import os
from pathlib import Path
from dotenv import load_dotenv

print("Current directory:", Path.cwd())
print(".env exists:", Path(".env").exists())

# Load explicitly
result = load_dotenv(dotenv_path=".env", verbose=True)
print(f"load_dotenv returned: {result}")

# Check what got loaded
print("\nEnvironment variables:")
for key in ["SENTINEL_HUB_CLIENT_ID", "SENTINEL_HUB_CLIENT_SECRET"]:
    val = os.getenv(key)
    print(f"  {key}: {val if val else 'NOT SET'}")

# Check file contents directly
print("\nFile contents:")
with open(".env", "r") as f:
    content = f.read()
    print(repr(content))
    
print("\nLines in file:")
with open(".env", "r") as f:
    for i, line in enumerate(f, 1):
        print(f"  Line {i}: {repr(line)}")
