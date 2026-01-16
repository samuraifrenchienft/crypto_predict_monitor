import os

print('=== CHECKING ACTUAL ENVIRONMENT VARIABLES ===')

# Check all Discord-related environment variables
discord_vars = [
    'DISCORD_WEBHOOK_URL',
    'CPM_WEBHOOK_URL', 
    'DISCORD_HEALTH_WEBHOOK_URL',
    'DISCORD_BOT_TOKEN'
]

print('\\n--- DISCORD ENVIRONMENT VARIABLES ---')
for var in discord_vars:
    value = os.getenv(var)
    if value:
        print(f'{var}: SET')
        print(f'  Length: {len(value)} chars')
        print(f'  Starts with: {value[:30]}...')
        print(f'  Ends with: ...{value[-20:]}')
    else:
        print(f'{var}: NOT SET')

# Check if .env file exists and what's in it
print('\\n--- .env FILE CHECK ---')
env_files = ['.env', '.env.txt', 'env_credentials.txt']

for env_file in env_files:
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            print(f'{env_file}: EXISTS ({len(content)} chars)')
            
            # Look for Discord webhooks in the file
            if 'DISCORD_WEBHOOK_URL' in content:
                lines = content.split('\\n')
                for line in lines:
                    if 'DISCORD_WEBHOOK_URL' in line and '=' in line:
                        print(f'  Found: {line.strip()[:80]}...')
            if 'CPM_WEBHOOK_URL' in content:
                lines = content.split('\\n')
                for line in lines:
                    if 'CPM_WEBHOOK_URL' in line and '=' in line:
                        print(f'  Found: {line.strip()[:80]}...')
            if 'DISCORD_HEALTH_WEBHOOK_URL' in content:
                lines = content.split('\\n')
                for line in lines:
                    if 'DISCORD_HEALTH_WEBHOOK_URL' in line and '=' in line:
                        print(f'  Found: {line.strip()[:80]}...')
    except FileNotFoundError:
        print(f'{env_file}: NOT FOUND')
    except Exception as e:
        print(f'{env_file}: ERROR - {e}')

# Test the actual webhooks from environment variables
print('\\n--- TESTING ACTUAL ENV WEBHOOKS ---')
webhook_urls = {
    'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
    'CPM_WEBHOOK_URL': os.getenv('CPM_WEBHOOK_URL'),
    'DISCORD_HEALTH_WEBHOOK_URL': os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
}

import requests

for name, url in webhook_urls.items():
    if url:
        print(f'\\nTesting {name}:')
        print(f'  URL: {url[:50]}...')
        
        try:
            test_message = {
                "content": f"Test from {name} - Environment Variable Check",
                "username": "Crypto Monitor"
            }
            
            response = requests.post(url, json=test_message, timeout=10)
            print(f'  Status: {response.status_code}')
            
            if response.status_code == 204:
                print(f'  Result: WORKING')
            elif response.status_code == 200:
                print(f'  Result: WORKING')
            else:
                print(f'  Result: FAILED - {response.text[:100]}')
                
        except Exception as e:
            print(f'  Error: {e}')
    else:
        print(f'\\n{name}: NOT SET')
