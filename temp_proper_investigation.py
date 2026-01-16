import os
import sys
import asyncio
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print('=== PROPER DISCORD ALERT INVESTIGATION ===')

# Check environment variables
print('\\n--- ENVIRONMENT VARIABLES ---')
env_vars = {
    'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
    'CPM_WEBHOOK_URL': os.getenv('CPM_WEBHOOK_URL'),
    'DISCORD_HEALTH_WEBHOOK_URL': os.getenv('DISCORD_HEALTH_WEB_WEBHOOK_URL'),
    'DISCORD_BOT_TOKEN': os.getenv('DISCORD_BOT_TOKEN')
}

for var, value in env_vars.items():
    if value:
        print(f'{var}: SET')
        print(f'  Value: {value}')
        print(f'  Length: {len(value)}')
    else:
        print(f'{var}: NOT SET')

# Check if alert system is actually running
print('\\n--- CHECKING IF ALERT SYSTEM IS RUNNING ---')
try:
    # Check if there are any processes running alert-related code
    import psutil
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(alert_keyword in cmdline.lower() for alert_keyword in ['alert', 'discord', 'webhook', 'arbitrage']):
                    processes.append((proc.info['pid'], proc.info['name'], cmdline))
        except:
            pass
    
    if processes:
        print(f'Found {len(processes)} alert-related processes:')
        for pid, name, cmdline in processes:
            print(f'  PID {pid}: {name}')
            print(f'  Command: {cmdline}')
    else:
        print('No alert-related processes found')
        
except Exception as e:
    print(f'Process check failed: {e}')

# Check if dashboard is running and has alert endpoints
print('\\n--- CHECKING DASHBOARD ALERT ENDPOINTS ---')
try:
    import requests
    
    # Check if dashboard is running
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            print('Dashboard is running')
            
            # Check for alert endpoints
            alert_endpoints = ['/api/alert', '/api/test/alert', '/api/arbitrage']
            for endpoint in alert_endpoints:
                try:
                    response = requests.get(f'http://localhost:5000{endpoint}', timeout=5)
                    print(f'{endpoint}: {response.status_code}')
                except:
                    print(f'{endpoint}: NOT AVAILABLE')
                    
        else:
            print(f'Dashboard not running (status: {response.status_code})')
            
    except requests.exceptions.ConnectionError:
        print('Dashboard not running (connection refused)')
    except Exception as e:
        print(f'Dashboard check failed: {e}')
        
except Exception as e:
    print(f'Dashboard check failed: {e}')

# Check the actual alert system code
print('\\n--- CHECKING ALERT SYSTEM CODE ---')
try:
    # Check if professional alerts can be imported and initialized
    from professional_alerts import ProfessionalArbitrageAlerts
    
    print('ProfessionalArbitrageAlerts class found')
    
    # Try to initialize it
    try:
        alerts = ProfessionalArbitrageAlerts()
        print(f'Alerts initialized with webhook: {alerts.webhook_url[:50] if alerts.webhook_url else "None"}...')
        
        # Check if it can send a test alert
        async def test_alert():
            try:
                async with alerts:
                    if not alerts.webhook_url:
                        print('ERROR: No webhook URL configured')
                        return False
                        
                    test_payload = {
                        "content": "DEBUG: Testing alert system",
                        "username": "Crypto Monitor Debug"
                    }
                    
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.post(alerts.webhook_url, json=test_payload) as response:
                            if response.status == 204:
                                print('SUCCESS: Test alert sent via ProfessionalArbitrageAlerts')
                                return True
                            else:
                                print(f'FAILED: Alert failed with status {response.status}')
                                text = await response.text()
                                print(f'Error: {text}')
                                return False
            except Exception as e:
                print(f'ERROR: Failed to send test alert: {e}')
                return False
        
        # Run the test
        result = asyncio.run(test_alert())
        print(f'Test alert result: {result}')
        
    except Exception as e:
        print(f'Alerts initialization failed: {e}')
        
except ImportError as e:
    print(f'ProfessionalArbitrageAlerts not found: {e}')

# Check bot alert manager
print('\\n--- CHECKING BOT ALERT MANAGER ---')
try:
    from utils.alert_manager import AlertManager
    
    print('AlertManager class found')
    
    # Check if it's initialized
    try:
        manager = AlertManager()
        print(f'AlertManager initialized')
        print(f'Discord alerter: {"CONFIGURED" if manager.discord_alerter else "NOT CONFIGURED"}')
        
        # Check if it can send alerts
        if manager.discord_alerter:
            print('Discord alerter is available - testing...')
            # Try to send a test
            try:
                success = manager.discord_alerter.send_alert("DEBUG", "Test alert from AlertManager")
                print(f'AlertManager test result: {"SUCCESS" if success else "FAILED"}')
            except Exception as e:
                print(f'AlertManager test failed: {e}')
        else:
            print('Discord alerter not configured')
            
    except Exception as e:
        print(f'AlertManager initialization failed: {e}')
        
except ImportError as e:
    print(f'AlertManager not found: {e}')

# Check if there are any recent alert logs
print('\\n--- CHECKING FOR ALERT LOGS ---')
log_files = ['crypto_predict_monitor.log', 'logs/app.log', 'logs/alerts.log']
for log_file in log_files:
    try:
        if os.path.exists(log_file):
            # Get last 10 lines of log file
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_lines = lines[-10:] if len(lines) > 10 else lines
                
                print(f'\\n{log_file} (last {len(recent_lines)} lines):')
                for line in recent_lines:
                    if 'alert' in line.lower() or 'discord' in line.lower() or 'webhook' in line.lower():
                        print(f'  {line.strip()}')
        else:
            print(f'{log_file}: NOT FOUND')
    except Exception as e:
        print(f'{log_file}: ERROR - {e}')

print('\\n--- CONCLUSION ---')
print('Based on the investigation above, the issue could be:')
print('1. Alert system not running/initialized')
print('2. Dashboard not running')
print('3. Alert system configuration issue')
print('4. Network/firewall blocking Discord requests')
print('5. Rate limiting or cooldown preventing alerts')
print('6. No actual arbitrage opportunities detected to trigger alerts')
print('')
print('Please share what you see above so I can identify the real issue!')
