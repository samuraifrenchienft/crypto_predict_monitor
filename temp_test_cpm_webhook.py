import os
import requests

print('=== TESTING CPM_WEBHOOK_URL DIRECTLY ===')

# Get the actual CPM_WEBHOOK_URL from environment
cpm_webhook = os.getenv('CPM_WEBHOOK_URL')
print(f'CPM_WEBHOOK_URL: {cpm_webhook}')
print(f'Length: {len(cpm_webhook) if cpm_webhook else "None"}')

if cpm_webhook:
    print('\\n--- TESTING CPM_WEBHOOK_URL ---')
    try:
        test_message = {
            "content": "🧪 Test from CPM_WEBHOOK_URL - Direct Environment Variable Test",
            "username": "CPM Monitor"
        }
        
        response = requests.post(cpm_webhook, json=test_message, timeout=10)
        print(f'Status: {response.status_code}')
        
        if response.status_code == 204:
            print('SUCCESS: CPM_WEBHOOK_URL is working!')
        elif response.status_code == 200:
            print('SUCCESS: CPM_WEBHOOK_URL is working!')
        else:
            print(f'FAILED: CPM_WEBHOOK_URL failed with status {response.status_code}')
            print(f'Error: {response.text}')
            
    except Exception as e:
        print(f'ERROR: Failed to test CPM_WEBHOOK_URL: {e}')
else:
    print('ERROR: CPM_WEBHOOK_URL is not set')

# Check what the professional alerts system is using
print('\\n--- CHECKING WHAT PROFESSIONAL ALERTS USES ---')
try:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    
    from professional_alerts import ProfessionalArbitrageAlerts
    
    alerts = ProfessionalArbitrageAlerts()
    print(f'ProfessionalArbitrageAlerts webhook: {alerts.webhook_url}')
    print(f'Length: {len(alerts.webhook_url) if alerts.webhook_url else "None"}')
    
    # Test what the professional alerts system is actually using
    if alerts.webhook_url:
        print('\\n--- TESTING PROFESSIONAL ALERTS WEBHOOK ---')
        try:
            test_message = {
                "content": "🧪 Test from ProfessionalArbitrageAlerts webhook",
                "username": "CPM Monitor"
            }
            
            response = requests.post(alerts.webhook_url, json=test_message, timeout=10)
            print(f'Status: {response.status_code}')
            
            if response.status_code == 204:
                print('SUCCESS: ProfessionalArbitrageAlerts webhook is working!')
            elif response.status_code == 200:
                print('SUCCESS: ProfessionalArbitrageAlerts webhook is working!')
            else:
                print(f'FAILED: ProfessionalArbitrageAlerts webhook failed with status {response.status_code}')
                print(f'Error: {response.text}')
                
        except Exception as e:
            print(f'ERROR: Failed to test ProfessionalArbitrageAlerts webhook: {e}')
    else:
        print('ERROR: ProfessionalArbitrageAlerts has no webhook URL')
        
except Exception as e:
    print(f'ERROR: Failed to check ProfessionalArbitrageAlerts: {e}')

print('\\n--- COMPARISON ---')
print(f'Environment CPM_WEBHOOK_URL: {cpm_webhook}')
print(f'ProfessionalArbitrageAlerts webhook: {alerts.webhook_url if alerts.webhook_url else "None"}')

if cpm_webhook and alerts.webhook_url:
    if cpm_webhook == alerts.webhook_url:
        print('✅ Both are using the same webhook URL')
    else:
        print('❌ They are using different webhook URLs')
        print(f'Environment: {cpm_webhook}')
        print(f'Professional: {alerts.webhook_url}')
else:
    print('❌ One or both webhook URLs are missing')
