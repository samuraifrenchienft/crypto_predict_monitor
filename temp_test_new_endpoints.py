import requests
import json

print('=== TESTING NEW DASHBOARD ALERT ENDPOINTS ===')

# Test the new alert endpoints
endpoints = [
    ('POST', '/api/test/alert', {'message': 'Test alert from new endpoint'}),
    ('POST', '/api/alert', {'type': 'info', 'message': 'Test general alert', 'severity': 'info'}),
    ('POST', '/api/alert', {'type': 'warning', 'message': 'Test warning alert', 'severity': 'warning'}),
    ('GET', '/api/arbitrage', None)
]

for method, endpoint, data in endpoints:
    print(f'\\n--- Testing {method} {endpoint} ---')
    
    try:
        if method == 'POST':
            response = requests.post(f'http://localhost:5000{endpoint}', json=data, timeout=10)
        else:
            response = requests.get(f'http://localhost:5000{endpoint}', timeout=10)
        
        print(f'Status: {response.status_code}')
        
        if response.status_code == 200:
            result = response.json()
            print(f'Result: {result}')
        else:
            print(f'Error: {response.text}')
            
    except Exception as e:
        print(f'Error: {e}')

print('\\n--- SUMMARY ---')
print('Alert endpoints have been added to the dashboard!')
print('You can now:')
print('1. POST /api/test/alert - Test Discord alerts')
print('2. POST /api/alert - Send custom alerts') 
print('3. GET /api/arbitrage - Get arbitrage opportunities')
print('\\nThese endpoints integrate with the ProfessionalArbitrageAlerts system!')
