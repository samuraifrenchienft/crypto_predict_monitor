"""
Frontend Integration Guide
How to integrate P&L Card Button into your React application
"""

# Frontend Integration for P&L Cards

## Quick Start

### 1. Install Dependencies
```bash
npm install lucide-react
# or
yarn add lucide-react
```

### 2. Copy React Component
Copy `src/components/PnLCardButton.jsx` to your frontend components directory.

### 3. Import and Use
```jsx
import PnLCardButton from './components/PnLCardButton';

function YourPnLPage({ user, pnlData }) {
  return (
    <div className="p-6">
      {/* Your existing P&L content */}
      
      {/* Add P&L Card Generator */}
      <div className="mt-8">
        <PnLCardButton 
          userId={user.id}
          currentPnL={pnlData}
          predictions={user.predictions || []}
        />
      </div>
    </div>
  );
}
```

## Integration Options

### Option 1: Standalone Button
Add to any page where users can generate P&L cards:

```jsx
// In your dashboard/profile page
<PnLCardButton userId={currentUser.id} />
```

### Option 2: P&L Popup Integration
Add to existing P&L popup/modal:

```jsx
// In your P&L modal component
<div className="pnl-modal">
  <div className="pnl-stats">
    {/* Existing stats display */}
  </div>
  
  <div className="pnl-card-section border-t">
    <h3>Share Your Results</h3>
    <PnLCardButton userId={user.id} currentPnL={stats} />
  </div>
</div>
```

### Option 3: Leaderboard Integration
Add to leaderboard page for top performers:

```jsx
// In leaderboard component
{leaderboard.map((user, index) => (
  <div key={user.id} className="leaderboard-row">
    <div className="rank">{index + 1}</div>
    <div className="user-info">
      <span>{user.username}</span>
      <span>{user.total_pnl}%</span>
    </div>
    <div className="actions">
      {index < 3 && (
        <PnLCardButton userId={user.id} compact={true} />
      )}
    </div>
  </div>
))}
```

## Styling Integration

### CSS Variables (Optional)
Add to your CSS for consistent theming:

```css
:root {
  --pnl-primary: #0001ff;
  --pnl-glow: rgba(0, 1, 255, 0.6);
  --pnl-bg-dark: #050540;
  --pnl-bg-light: #151560;
}
```

### Tailwind CSS Classes
The component uses Tailwind classes. Ensure your config includes:

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'pnl-blue': '#0001ff',
      },
      boxShadow: {
        'pnl-glow': '0 0 20px rgba(0, 1, 255, 0.6)',
      }
    }
  }
}
```

## API Configuration

### Update API Base URL
If your backend runs on a different URL/domain:

```jsx
// In PnLCardButton.jsx, update the fetch calls:
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Then use:
const response = await fetch(`${API_BASE_URL}/api/pnl-card/${userId}/share`, {
  // ... rest of fetch
});
```

### Environment Variables
Create `.env` in your frontend:

```bash
REACT_APP_API_URL=http://localhost:5000
REACT_APP_ENVIRONMENT=development
```

## Authentication Integration

### JWT Token Handling
Update the component to use your auth system:

```jsx
// Replace the simple token logic with your auth:
const getToken = () => {
  // Example with Auth0
  return auth0Client.getAccessTokenSilently();
  
  // Example with Firebase
  return firebase.auth().currentUser.getIdToken();
  
  // Example with custom auth
  return localStorage.getItem('authToken');
};
```

### User Context
Integrate with your user context/state management:

```jsx
import { useUser } from './contexts/UserContext';

function PnLCardIntegrated() {
  const { user } = useUser();
  
  if (!user) {
    return <div>Please login to generate P&L cards</div>;
  }
  
  return <PnLCardButton userId={user.id} />;
}
```

## Error Handling

### Custom Error Messages
Update error handling to match your UI:

```jsx
// In the error state:
<div className="error-container">
  <p className="error-message">{error}</p>
  <button onClick={retryGeneration} className="retry-button">
    Try Again
  </button>
</div>
```

### Loading States
Customize loading to match your design:

```jsx
// Replace with your loading component:
{isGenerating && (
  <div className="loading-spinner">
    <div className="spinner"></div>
    <p>Generating your viral P&L card...</p>
  </div>
)}
```

## Mobile Responsiveness

The component is mobile-responsive, but you may want to adjust:

```css
/* Custom mobile styles */
@media (max-width: 768px) {
  .pnl-card-container {
    padding: 1rem;
  }
  
  .pnl-card-preview img {
    max-height: 300px;
  }
  
  .share-buttons {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }
}
```

## Testing Integration

### Component Testing
```jsx
// PnLCardButton.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import PnLCardButton from './PnLCardButton';

test('generates card on click', async () => {
  render(<PnLCardButton userId="test_user" />);
  
  const button = screen.getByText('Generate P&L Card');
  fireEvent.click(button);
  
  expect(screen.getByText('Generating your P&L card...')).toBeInTheDocument();
});
```

### API Mocking
```jsx
// Mock the API for testing
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ share_text: 'Test share text' })
  })
);
```

## Performance Tips

### Lazy Loading
```jsx
// Lazy load the component
const PnLCardButton = React.lazy(() => import('./PnLCardButton'));

// Use with Suspense
<Suspense fallback={<div>Loading...</div>}>
  <PnLCardButton userId={user.id} />
</Suspense>
```

### Image Optimization
```jsx
// Add loading="lazy" to card images
<img 
  src={cardUrl} 
  alt="P&L Card" 
  loading="lazy"
  className="max-w-full h-auto rounded-lg"
/>
```

## Deployment Notes

### Build Configuration
Ensure your build process includes JSX files:

```javascript
// webpack.config.js or similar
module.exports = {
  module: {
    rules: [
      {
        test: /\.jsx$/,
        use: 'babel-loader',
        exclude: /node_modules/
      }
    ]
  }
};
```

### Environment Variables
Make sure to set production environment variables:

```bash
# Production build
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_ENVIRONMENT=production
```

That's it! Your P&L card system is now fully integrated into your frontend application.
