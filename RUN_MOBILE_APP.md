# Full Commands to Run the AI Road Trip Mobile App

## File Paths
- **Project Root**: `C:\Users\jared\OneDrive\Desktop\RoadTrip`
- **Mobile App**: `C:\Users\jared\OneDrive\Desktop\RoadTrip\mobile`
- **Backend URL**: https://roadtrip-backend-minimal-792001900150.us-central1.run.app

## Commands to Run

### Option 1: Using Windows Command Prompt (CMD)
```cmd
cd C:\Users\jared\OneDrive\Desktop\RoadTrip\mobile
npm start
```

### Option 2: Using PowerShell
```powershell
cd C:\Users\jared\OneDrive\Desktop\RoadTrip\mobile
npm start
```

### Option 3: Using Git Bash
```bash
cd /c/Users/jared/OneDrive/Desktop/RoadTrip/mobile
npm start
```

## Step-by-Step Instructions

1. **Open Terminal**:
   - Press `Win + R`, type `cmd`, press Enter
   - Or search for "Command Prompt" in Start Menu

2. **Navigate to Mobile Directory**:
   ```cmd
   cd C:\Users\jared\OneDrive\Desktop\RoadTrip\mobile
   ```

3. **Install Dependencies** (if not already done):
   ```cmd
   npm install
   ```

4. **Start the App**:
   ```cmd
   npm start
   ```

5. **Run on Device**:
   - Press `i` for iOS simulator
   - Press `a` for Android emulator
   - Press `w` for web browser
   - Scan QR code with Expo Go app on your phone

## Quick One-Liner

Copy and paste this entire command:
```cmd
cd C:\Users\jared\OneDrive\Desktop\RoadTrip\mobile && npm start
```

## Troubleshooting

If you get "npm is not recognized":
1. Install Node.js from https://nodejs.org/
2. Restart your terminal
3. Try again

If you get "Cannot find module":
```cmd
cd C:\Users\jared\OneDrive\Desktop\RoadTrip\mobile
npm install
npm start
```

## Verify Backend Connection

The app should automatically connect to:
https://roadtrip-backend-minimal-792001900150.us-central1.run.app

You can test the backend directly:
```cmd
curl https://roadtrip-backend-minimal-792001900150.us-central1.run.app/health
```

Or open in browser:
https://roadtrip-backend-minimal-792001900150.us-central1.run.app/docs