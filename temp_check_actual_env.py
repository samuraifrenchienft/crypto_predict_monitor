import os
import requests

print('=== CHECKING ACTUAL ENVIRONMENT VARIABLES ===')

# Check what's actually set
print('\\n--- CURRENT ENVIRONMENT VARIABLES ---')
env_vars = [
    'DISCORD_WEBHOOK_URL',
    'CPM_WEBHOOK_URL', 
    'DISCORD_HEALTH_WEBHOOK_URL',
    'DISCORD_BOT_TOKEN'
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f'{var}: SET')
        print(f'  Full URL: {value}')
        print(f'  Length: {len(value)} chars')
    else:
        print(f'{var}: NOT SET')

# Test each webhook that's actually set
print('\\n--- TESTING ACTUAL WEBHOOKS ---')
webhook_urls = {
    'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
    'CPM_WEBHOOK_URL': os.getenv('CPM_WEBHOOK_URL'),
    'DISCORD_HEALTH_WEBHOOK_URL': os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
}

for name, url in webhook_urls.items():
    if url:
        print(f'\\nTesting {name}:')
        print(f'  URL: {url}')
        
        try:
            test_message = {
                "content": f"Test from {name} - Environment Variable Test",
                "username": "Crypto Monitor"
            }
            
            response = requests.post(url, json=test_message, timeout=10)
            print(f'  Status: {response.status_code}')
            
            if response.status_code == 204:
                print(f'  Result: WORKING ✓')
            elif response.status_code == 200:
                print(f'  Result: WORKING ✓')
            else:
                print(f'  Result: FAILED ❌')
                print(f'  Error: {response.text}')
                
        except Exception as e:
            print(f'  Error: {e}')
    else:
        print(f'\\n{name}: NOT SET')

# Check what's in .env files
print('\\n--- .env FILES CONTENT ---')
env_files = ['.env', '.env.txt', 'env_credentials.txt']

for env_file in env_files:
    try:
        with open(env_file, 'r') as f:
            content = f.read()
            print(f'\\n{env_file}:')
            
            # Look for Discord webhooks
            lines = content.split('\\n')
            for line in lines:
                if any(webhook in line for webhook in ['DISCORD_WEBHOOK_URL', 'CPM_WEBHOOK_URL', 'DISCORD_HEALTH_WEBHOOK_URL']) and '=' in line:
                    print(f'  {line.strip()}')
                    
    except FileNotFoundError:
        print(f'\\n{env_file}: NOT FOUND')
    except Exception as e:
        print(f'\\n{env_file}: ERROR - {e}')

print('\\n--- CONCLUSION ---')
print('Let me know exactly what you see above so I can fix the actual issue!')
