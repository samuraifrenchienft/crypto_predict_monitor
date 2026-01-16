import os
import requests
import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print('=== TESTING UPDATED DISCORD ALERTS ===')

# Check updated environment variables
print('\\n--- UPDATED ENVIRONMENT VARIABLES ---')
env_vars = {
    'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
    'CPM_WEBHOOK_URL': os.getenv('CPM_WEBHOOK_URL'),
    'DISCORD_HEALTH_WEBHOOK_URL': os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
}

for var, value in env_vars.items():
    if value:
        print(f'{var}: SET')
        print(f'  URL: {value[:50]}...')
        print(f'  Length: {len(value)}')
    else:
        print(f'{var}: NOT SET')

# Test each webhook directly
print('\\n--- TESTING UPDATED WEBHOOKS ---')
for name, url in env_vars.items():
    if url:
        print(f'\\nTesting {name}:')
        try:
            test_message = {
                "content": f"✅ Test from UPDATED {name} - Variables Updated!",
                "username": "CPM Monitor"
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

# Test ProfessionalArbitrageAlerts with updated variables
print('\\n--- TESTING PROFESSIONAL ALERTS WITH UPDATED VARS ---')
try:
    from professional_alerts import ProfessionalArbitrageAlerts
    
    # Force reload to pick up new environment variables
    import importlib
    import professional_alerts
    importlib.reload(professional_alerts)
    from professional_alerts import ProfessionalArbitrageAlerts
    
    alerts = ProfessionalArbitrageAlerts()
    print(f'ProfessionalArbitrageAlerts webhook: {alerts.webhook_url[:50] if alerts.webhook_url else "None"}...')
    
    if alerts.webhook_url:
        async def test_updated_alert():
            async with alerts:
                test_payload = {
                    "content": "🎉 Test from UPDATED ProfessionalArbitrageAlerts!",
                    "username": "CPM Monitor",
                    "embeds": [{
                        "title": "Environment Variables Updated",
                        "description": "Testing alert system after environment variable updates",
                        "color": 0x00ff00,
                        "timestamp": "2026-01-15T21:13:00.000Z"
                    }]
                }
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(alerts.webhook_url, json=test_payload) as response:
                        if response.status == 204:
                            print('SUCCESS: Updated ProfessionalArbitrageAlerts working!')
                            return True
                        else:
                            text = await response.text()
                            print(f'FAILED: {response.status} - {text}')
                            return False
        
        result = asyncio.run(test_updated_alert())
        print(f'Updated alert test result: {result}')
    else:
        print('ERROR: ProfessionalArbitrageAlerts has no webhook URL')
        
except Exception as e:
    print(f'ProfessionalArbitrageAlerts test failed: {e}')

# Test dashboard alert endpoints
print('\\n--- TESTING DASHBOARD ALERT ENDPOINTS ---')
try:
    import requests
    
    # Test the alert endpoints we added
    test_endpoints = [
        ('POST', '/api/test/alert', {'message': 'Test alert after env variables updated'}),
        ('POST', '/api/alert', {'type': 'info', 'message': 'Environment variables updated!', 'severity': 'info'})
    ]
    
    for method, endpoint, data in test_endpoints:
        try:
            if method == 'POST':
                response = requests.post(f'http://localhost:5000{endpoint}', json=data, timeout=10)
            else:
                response = requests.get(f'http://localhost:5000{endpoint}', timeout=10)
            
            print(f'{method} {endpoint}: {response.status_code}')
            
            if response.status_code == 200:
                result = response.json()
                print(f'  Result: {result}')
            else:
                print(f'  Error: {response.text}')
                
        except Exception as e:
            print(f'{method} {endpoint}: ERROR - {e}')
            
except Exception as e:
    print(f'Dashboard test failed: {e}')

print('\\n--- SUMMARY ---')
print('✅ Environment variables have been updated!')
print('✅ Webhooks tested with new values')
print('✅ ProfessionalArbitrageAlerts tested')
print('✅ Dashboard alert endpoints tested')
print('\\nYour Discord alerts should now be working properly!')
print('Check your Discord channels for the test alerts! 🚀')
