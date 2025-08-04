# AI Road Trip Mobile App - Quick Start Guide (Development)

This guide helps you get the AI Road Trip mobile app running locally for development and testing.

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Expo CLI (`npm install -g expo-cli`)
- iOS Simulator (Mac only) or Android Emulator
- Expo Go app on your physical device (optional)

## Quick Start

### 1. Install Dependencies

```bash
cd mobile
npm install
```

### 2. Environment Configuration

The `.env` file has been configured for local development:
- API URL: `http://localhost:8000`
- Development mode enabled
- Mock data available when backend is offline

### 3. Start the Mobile App

```bash
# Start Expo development server
npm start

# Or start with specific platform
npm run ios      # iOS Simulator (Mac only)
npm run android  # Android Emulator
```

### 4. Running on Physical Device

1. Install the Expo Go app from App Store or Google Play
2. Scan the QR code shown in terminal or browser
3. If using a physical device, update `.env` with your computer's IP:
   ```
   EXPO_PUBLIC_API_URL=http://YOUR_COMPUTER_IP:8000
   ```

## Development Features

### Mock Data Mode
When the backend is unavailable, the app automatically uses mock data:
- Mock voice responses
- Sample stories about San Francisco locations
- Simulated navigation routes

### Disabled in Development
For easier development, these features are disabled:
- Certificate pinning
- Jailbreak/root detection
- Sentry crash reporting (unless configured)

### Available Commands

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint

# Start in MVP mode
npm run start:mvp
```

## Common Issues & Solutions

### 1. Metro Bundler Issues
```bash
# Clear Metro cache
npx expo start -c
```

### 2. Module Resolution Errors
```bash
# Clear all caches
rm -rf node_modules
npm install
npx expo start -c
```

### 3. Backend Connection Issues
- Ensure backend is running on `http://localhost:8000`
- For physical devices, use your computer's IP address
- Check firewall settings allow connections on port 8000

### 4. Permission Errors
The app will request permissions for:
- Location (for navigation features)
- Microphone (for voice commands)
- Camera (for AR features - disabled in dev)

Grant these permissions when prompted or go to device settings.

## Testing the App

### Without Backend
1. Start the app: `npm start`
2. The app will use mock data automatically
3. Test navigation, voice commands, and story generation

### With Backend
1. Start the backend: `cd ../backend && uvicorn app.main:app --reload`
2. Start the mobile app: `cd mobile && npm start`
3. Full functionality will be available

## Key Features to Test

1. **Onboarding Flow**
   - Welcome screens
   - Permission requests
   - Voice personality selection

2. **Main Experience**
   - Voice assistant interaction
   - Story generation for locations
   - Navigation features

3. **Settings**
   - Language selection
   - Accessibility options
   - Offline content management

## Debug Mode

The app includes development logging. View logs in:
- Terminal where Expo is running
- Browser developer console (for web)
- React Native Debugger (if installed)

## Next Steps

1. Once the backend is fixed, update `.env` with the production API URL
2. Test all features with real API integration
3. Run the full test suite: `npm test`
4. Build for production when ready

## Support

For issues or questions:
- Check the main README.md for architecture details
- Review CLAUDE.md for AI development guidelines
- Check mobile/docs/ for detailed documentation