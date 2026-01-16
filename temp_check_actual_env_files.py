import os

print('=== CHECKING ACTUAL ENVIRONMENT FILES ===')

# Check all possible env files
env_files = ['.env', '.env.txt', 'env_credentials.txt']

for env_file in env_files:
    print(f'\\n--- {env_file} ---')
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            print(f'File exists ({len(content)} chars)')
            
            # Look for Discord webhooks
            lines = content.split('\\n')
            for line in lines:
                if any(webhook in line for webhook in ['DISCORD_WEBHOOK_URL', 'CPM_WEBHOOK_URL', 'DISCORD_HEALTH_WEBHOOK_URL']) and '=' in line and not line.strip().startswith('#'):
                    print(f'  {line.strip()}')
                    
    except FileNotFoundError:
        print(f'File NOT FOUND')
    except Exception as e:
        print(f'Error reading file: {e}')

# Check what Python is actually seeing
print('\\n--- WHAT PYTHON SEES ---')
env_vars = {
    'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
    'CPM_WEBHOOK_URL': os.getenv('CPM_WEBHOOK_URL'),
    'DISCORD_HEALTH_WEBHOOK_URL': os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
}

for var, value in env_vars.items():
    if value:
        print(f'{var}: {value}')
    else:
        print(f'{var}: NOT SET')

print('\\n--- ENVIRONMENT LOADING CHECK ---')
# Check if .env file is being loaded
try:
    from dotenv import load_dotenv
    result = load_dotenv()
    print(f'load_dotenv() result: {result}')
    
    # Check again after loading
    print('\\nAfter load_dotenv():')
    for var, value in env_vars.items():
        actual_value = os.getenv(var)
        print(f'{var}: {"SET" if actual_value else "NOT SET"}')
        if actual_value:
            print(f'  Value: {actual_value}')
            
except ImportError:
    print('dotenv not installed')
except Exception as e:
    print(f'Error loading dotenv: {e}')

print('\\n--- PYTHON ENVIRONMENT CHECK ---')
# Check all environment variables that contain "discord" or "webhook"
all_env = dict(os.environ())
for key, value in all_env.items():
    if any(keyword in key.lower() for keyword in ['discord', 'webhook', 'cpm']):
        print(f'{key}: {value[:50]}...' if len(value) > 50 else f'{key}: {value}')
