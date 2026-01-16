import os
import requests

print('=== TESTING RENDER ENVIRONMENT VARIABLES ===')

# Check all Discord-related environment variables
print('\\n--- RENDER ENVIRONMENT VARIABLES ---')
env_vars = [
    'DISCORD_WEBHOOK_URL',
    'CPM_WEBHOOK_URL', 
    'DISCORD_HEALTH_WEBHOOK_URL',
    'DISCORD_BOT_TOKEN',
    'CPM_BASE_URL',
    'SUPABASE_URL',
    'ALCHEMY_API_KEY'
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f'{var}: SET')
        print(f'  Length: {len(value)} chars')
        print(f'  Starts with: {value[:30]}...')
        print(f'  Ends with: ...{value[-20:]}')
        
        # Check if it looks like a real webhook URL
        if 'webhook' in var.lower() and 'discord.com/api/webhooks' in value:
            # Extract webhook ID to check if it's real
            parts = value.split('/')
            if len(parts) >= 7:
                webhook_id = parts[5]
                if webhook_id.isdigit() and len(webhook_id) >= 17:
                    print(f'  Webhook ID: {webhook_id} (REAL)')
                else:
                    print(f'  Webhook ID: {webhook_id} (FAKE/PLACEHOLDER)')
        
    else:
        print(f'{var}: NOT SET')

# Test webhook URLs that are set
print('\\n--- TESTING RENDER WEBHOOKS ---')
webhook_urls = {
    'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
    'CPM_WEBHOOK_URL': os.getenv('CPM_WEBHOOK_URL'),
    'DISCORD_HEALTH_WEBHOOK_URL': os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
}

for name, url in webhook_urls.items():
    if url:
        print(f'\\nTesting {name}:')
        print(f'  URL: {url[:50]}...')
        
        try:
            test_message = {
                "content": f"🧪 Test from RENDER {name} - Environment Variable Check",
                "username": "CPM Monitor - Render"
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

# Test if we can access Render-specific endpoints
print('\\n--- RENDER-SPECIFIC CHECKS ---')
render_vars = [
    'RENDER_EXTERNAL_URL',
    'RENDER_EXTERNAL_HOSTNAME',
    'PORT',
    'NODE_ENV'
]

for var in render_vars:
    value = os.getenv(var)
    if value:
        print(f'{var}: {value}')
    else:
        print(f'{var}: NOT SET')

# Check if we're running on Render
print('\\n--- PLATFORM DETECTION ---')
if os.getenv('RENDER_EXTERNAL_URL'):
    print('Platform: Render (detected)')
    print(f'External URL: {os.getenv("RENDER_EXTERNAL_URL")}')
elif os.getenv('DYNO'):
    print('Platform: Heroku (detected)')
else:
    print('Platform: Local/Other (no Render/Heroku vars detected)')

print('\\n--- SUMMARY ---')
print('ENVIRONMENT STATUS:')
for var in env_vars:
    value = os.getenv(var)
    status = '✅ SET' if value else '❌ NOT SET'
    print(f'  {var}: {status}')

print('\\nWEBHOOK STATUS:')
for name, url in webhook_urls.items():
    if url and 'discord.com/api/webhooks' in url:
        parts = url.split('/')
        webhook_id = parts[5] if len(parts) >= 7 else 'unknown'
        if webhook_id.isdigit() and len(webhook_id) >= 17:
            print(f'  {name}: ✅ REAL WEBHOOK')
        else:
            print(f'  {name}: ❌ FAKE/PLACEHOLDER')
    else:
        print(f'  {name}: ❌ NOT SET/INVALID')

print('\\nIf webhooks show as REAL, your Discord alerts should work on Render!')
