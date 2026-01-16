import requests

print('=== TESTING REAL WEBHOOKS FROM .env.txt ===')

real_webhooks = {
    'Main': 'https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV',
    'Health': 'https://discord.com/api/webhooks/1455877944005365814/TpDNqyFu6XhD6SKgOMPssuBozVJ2HJvFa2fOMSqtOnyw6t5zaTx3F53TAcpDbLYpCeXb',
    'CPM': 'https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV'
}

for name, url in real_webhooks.items():
    try:
        test_message = {
            "content": f"Test from REAL {name} webhook - Environment Fix Test",
            "username": "Crypto Monitor"
        }
        
        response = requests.post(url, json=test_message, timeout=10)
        print(f'{name} webhook: {"WORKING" if response.status_code == 204 else "FAILED"} (Status: {response.status_code})')
        
    except Exception as e:
        print(f'{name} webhook: ERROR - {e}')

print('\\n--- SOLUTION ---')
print('The issue is that your environment variables are not set correctly.')
print('You need to set them to use the REAL webhook URLs from .env.txt')
print('')
print('PowerShell commands to fix:')
print('$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV"')
print('$env:CPM_WEBHOOK_URL="https://discord.com/api/webhooks/1461018352012230797/qsKOPbw4Qnk7NJN5Hh0bqRIpRRnYuU1nddNa4aPAJSVgb2eumdTYS6EmJDp3fVda81WV"')
print('$env:DISCORD_HEALTH_WEBHOOK_URL="https://discord.com/api/webhooks/1455877944005365814/TpDNqyFu6XhD6SKgOMPssuBozVJ2HJvFa2fOMSqtOnyw6t5zaTx3F53TAcpDbLYpCeXb"')
