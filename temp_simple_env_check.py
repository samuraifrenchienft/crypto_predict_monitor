import os

print('=== SIMPLE RENDER ENV CHECK ===')

# Just check what environment variables are actually set
print('Current environment variables:')
discord_vars = ['DISCORD_WEBHOOK_URL', 'CPM_WEBHOOK_URL', 'DISCORD_HEALTH_WEBHOOK_URL']

for var in discord_vars:
    value = os.getenv(var)
    if value:
        print(f'{var}: SET')
        if 'discord.com/api/webhooks' in value:
            # Extract webhook ID to check if real
            parts = value.split('/')
            if len(parts) >= 7:
                webhook_id = parts[5]
                if webhook_id.isdigit() and len(webhook_id) >= 17:
                    print(f'  Status: REAL WEBHOOK (ID: {webhook_id})')
                else:
                    print(f'  Status: FAKE/PLACEHOLDER (ID: {webhook_id})')
        else:
            print(f'  Status: Not a Discord webhook')
    else:
        print(f'{var}: NOT SET')

print('\\nTo check on Render:')
print('1. Go to your Render service dashboard')
print('2. Click "Environment" tab')
print('3. Look for the 3 webhook variables above')
print('4. Make sure they have real Discord webhook URLs')
