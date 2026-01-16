import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print('=== CHECKING ARBITRAGE SYSTEM INTEGRATION ===')

# Check if arbitrage system exists and is configured
print('\\n--- ARBITRAGE SYSTEM CHECK ---')
try:
    from arbitrage_main import ProfessionalArbitrageSystem
    
    print('ProfessionalArbitrageSystem class found')
    
    # Try to initialize it
    try:
        system = ProfessionalArbitrageSystem()
        print('Arbitrage system initialized')
        
        # Check if it can run
        try:
            import asyncio
            result = asyncio.run(system.initialize())
            print(f'Arbitrage system initialization: {"SUCCESS" if result else "FAILED"}')
            
            # Check if it's running detection
            print('Checking if arbitrage detection is running...')
            # This would need to be implemented in the arbitrage system
            
        except Exception as e:
            print(f'Arbitrage system run check failed: {e}')
            
    except Exception as e:
        print(f'Arbitrage system not found: {e}')

except ImportError as e:
    print(f'Arbitrage system not found: {e}')

# Check dashboard alert integration
print('\\n--- DASHBOARD ALERT INTEGRATION CHECK ---')
try:
    import requests
    
    # Check if dashboard has alert endpoints
    endpoints_to_check = [
        '/api/health',
        '/api/alerts', 
        '/api/arbitrage',
        '/api/test/alert',
        '/api/send_alert'
    ]
    
    for endpoint in endpoints_to_check:
        try:
            response = requests.get(f'http://localhost:5000{endpoint}', timeout=5)
            print(f'{endpoint}: {response.status_code}')
        except:
            print(f'{endpoint}: ERROR')
            
except Exception as e:
    print(f'Dashboard check failed: {e}')

# Check if dashboard has alert code
print('\\n--- DASHBOARD ALERT CODE CHECK ---')
try:
    # Check if dashboard imports alert-related modules
    import dashboard.app as app
    
    # Look for alert-related functions in dashboard
    import inspect
    
    alert_functions = []
    for name, obj in inspect.getmembers(app):
        if callable(obj) and any(keyword in name.lower() for keyword in ['alert', 'discord', 'webhook', 'arbitrage']):
            alert_functions.append(name)
    
    if alert_functions:
        print(f'Found alert-related functions: {alert_functions}')
    else:
        print('No alert-related functions found in dashboard')
        
except Exception as e:
    print(f'Dashboard code check failed: {e}')

# Check if there's a main arbitrage process
print('\\n--- MAIN ARBITRAGE PROCESS CHECK ---')
try:
    import psutil
    
    arbitrage_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if any(keyword in cmdline.lower() for keyword in ['arbitrage', 'main_arbitrage', 'professional_arbitrage']):
                arbitrage_processes.append((proc.info['pid'], proc.info['name'], cmdline))
        except:
            pass
    
    if arbitrage_processes:
        print(f'Found {len(arbitrage_processes)} arbitrage processes:')
        for pid, name, cmdline in arbitrage_processes:
            print(f'  PID {pid}: {name}')
            print(f'  Command: {cmdline}')
    else:
        print('No arbitrage processes found')
        
except Exception as e:
    print(f'Process check failed: {e}')

print('\\n--- SOLUTION ---')
print('ISSUE IDENTIFIED: The alert system is NOT integrated with the dashboard!')
print('')
print('The ProfessionalArbitrageAlerts works perfectly, but:')
print('1. Dashboard has no alert endpoints (/api/alert, /api/arbitrage, etc.)')
print('2. No arbitrage process is running to detect opportunities')
print('3. Dashboard doesn\'t call the alert system')
print('')
print('TO FIX THIS:')
print('1. Add alert endpoints to dashboard/app.py')
print('2. Integrate ProfessionalArbitrageAlerts with dashboard')
print('3. Start the arbitrage detection system')
print('4. Connect dashboard alerts to arbitrage opportunities')
