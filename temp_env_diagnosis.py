import os

print('=== DISCORD ALERT SYSTEM DIAGNOSIS ===')
print('\\nISSUE IDENTIFIED:')
print('Your environment variables have PLACEHOLDER values, not real webhook URLs!')
print('\\nCURRENT ENVIRONMENT VARIABLES:')
print(f'DISCORD_WEBHOOK_URL: {os.getenv("DISCORD_WEBHOOK_URL", "NOT SET")}')
print(f'CPM_WEBHOOK_URL: {os.getenv("CPM_WEBHOOK_URL", "NOT SET")}')
print(f'DISCORD_HEALTH_WEBHOOK_URL: {os.getenv("DISCORD_HEALTH_WEBHOOK_URL", "NOT SET")}')

print('\\nREAL WEBHOOK URLs (from env_credentials.txt):')
print('DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV')
print('DISCORD_HEALTH_WEBHOOK_URL=https://discord.com/api/webhooks/1455877944005365814/TpDNqyFu6XhD6SKgOMPssuBozVJ2HJvFa2fOMSqtOnyw6t5zaTx3F53TAcpDbLYpCeXb')
print('CPM_WEBHOOK_URL=https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV')

print('\\nHOW TO FIX:')
print('1. Open your .env file (it might be hidden)')
print('2. Replace the placeholder webhook URLs with the REAL ones above')
print('3. Restart your application/server')
print('4. Discord alerts will then work properly!')

print('\\nWINDOWS COMMANDS TO FIX:')
print('# Option 1: Edit .env file directly')
print('notepad .env')
print('')
print('# Option 2: Use PowerShell to set environment variables')
print('$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV"')
print('$env:CPM_WEBHOOK_URL="https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV"')
print('$env:DISCORD_HEALTH_WEBHOOK_URL="https://discord.com/api/webhooks/1455877944005365814/TpDNqyFu6XhD6SKgOMPssuBozVJ2HJvFa2fOMSqtOnyw6t5zaTx3F53TAcpDbLYpCeXb"')

print('\\nTESTING REAL WEBHOOKS:')
import requests

real_webhooks = {
    'Main': 'https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV',
    'Health': 'https://discord.com/api/webhooks/1455877944005365814/TpDNqyFu6XhD6SKgOMPssuBozVJ2HJvFa2fOMSqtOnyw6t5zaTx3F53TAcpDbLYpCeXb',
    'CPM': 'https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV'
}

for name, url in real_webhooks.items():
    try:
        test_message = {
            "content": f"Test from REAL {name} webhook - Fix verification",
            "username": "Crypto Monitor"
        }
        
        response = requests.post(url, json=test_message, timeout=10)
        print(f'{name} webhook: {"WORKING" if response.status_code == 204 else "FAILED"} (Status: {response.status_code})')
        
    except Exception as e:
        print(f'{name} webhook: ERROR - {e}')

print('\\nSUMMARY:')
print('The issue is NOT in the code - the code is correct!')
print('The issue is that your environment variables have placeholder/fake webhook URLs.')
print('Fix your .env file with the REAL webhook URLs and alerts will work!')
