import requests
import json

print('=== TESTING RENDER ENVIRONMENT VARIABLES ===')

# Test your deployed Render app to see what environment variables it has
render_urls = [
    'https://crypto-predict-monitor.onrender.com',
    'https://crypto-predict-monitor-2.onrender.com', 
    'https://cpm-arbitrage.onrender.com',
    'https://cpm-monitor.onrender.com'
]

print('\\n--- TESTING RENDER DEPLOYMENTS ---')

for url in render_urls:
    print(f'\\nTesting {url}:')
    try:
        # Test health endpoint
        response = requests.get(f'{url}/api/health', timeout=10)
        print(f'  Health endpoint: {response.status_code}')
        
        if response.status_code == 200:
            health_data = response.json()
            print(f'  Status: {health_data.get("status", "unknown")}')
            print(f'  Version: {health_data.get("version", "unknown")}')
            
            # Test environment variables endpoint (if it exists)
            try:
                env_response = requests.get(f'{url}/api/debug/env', timeout=10)
                if env_response.status_code == 200:
                    env_data = env_response.json()
                    print(f'  Environment variables available')
                    
                    # Check Discord webhooks
                    discord_vars = ['DISCORD_WEBHOOK_URL', 'CPM_WEBHOOK_URL', 'DISCORD_HEALTH_WEBHOOK_URL']
                    for var in discord_vars:
                        if var in env_data:
                            value = env_data[var]
                            print(f'    {var}: {"SET" if value else "NOT SET"}')
                            if value and 'discord.com/api/webhooks' in value:
                                parts = value.split('/')
                                if len(parts) >= 7:
                                    webhook_id = parts[5]
                                    if webhook_id.isdigit() and len(webhook_id) >= 17:
                                        print(f'      Webhook ID: {webhook_id} (REAL)')
                                    else:
                                        print(f'      Webhook ID: {webhook_id} (FAKE)')
                        else:
                            print(f'    {var}: NOT FOUND')
                else:
                    print(f'  Env debug endpoint: {env_response.status_code}')
            except:
                print(f'  No env debug endpoint available')
                
            # Test alert endpoint
            try:
                alert_test = {
                    "type": "test",
                    "message": "Testing Render environment variables",
                    "severity": "info"
                }
                alert_response = requests.post(f'{url}/api/alert', json=alert_test, timeout=10)
                print(f'  Alert endpoint: {alert_response.status_code}')
                
                if alert_response.status_code == 200:
                    alert_result = alert_response.json()
                    print(f'  Alert result: {alert_result}')
                else:
                    print(f'  Alert error: {alert_response.text[:100]}')
                    
            except:
                print(f'  Alert endpoint not available')
                
        else:
            print(f'  Health check failed: {response.text[:100]}')
            
    except requests.exceptions.ConnectionError:
        print(f'  Connection failed - service not available')
    except requests.exceptions.Timeout:
        print(f'  Request timeout')
    except Exception as e:
        print(f'  Error: {e}')

print('\\n--- TESTING ENVIRONMENT VARIABLES DIRECTLY ---')
# Try to test environment variables by making a request that would use them
test_payload = {
    "message": "Testing if Render environment variables are set correctly",
    "test_type": "env_check"
}

for url in render_urls:
    try:
        response = requests.post(f'{url}/api/test/alert', json=test_payload, timeout=10)
        print(f'{url} test alert: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'  Result: {result}')
        elif response.status_code == 404:
            print(f'  Endpoint not found')
        else:
            print(f'  Error: {response.text[:100]}')
            
    except Exception as e:
        print(f'{url} test failed: {e}')

print('\\n--- SUMMARY ---')
print('To check your Render environment variables:')
print('1. Go to your Render dashboard')
print('2. Select your service')
print('3. Go to "Environment" tab')
print('4. Check if these are set:')
print('   - DISCORD_WEBHOOK_URL')
print('   - CPM_WEBHOOK_URL') 
print('   - DISCORD_HEALTH_WEBHOOK_URL')
print('\\nMake sure they use REAL webhook URLs, not placeholders!')
