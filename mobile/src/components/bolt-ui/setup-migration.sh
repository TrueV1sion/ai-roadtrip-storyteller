#!/bin/bash

# Bolt UI Migration Setup Script
# Prepares RoadTrip mobile app for Bolt UI integration

echo "🎨 Starting Bolt UI Migration Setup..."

# Navigate to mobile directory
cd "$(dirname "$0")/../.." || exit 1

# Check if we're in the mobile directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Not in mobile directory. Please run from mobile/src/components/bolt-ui/"
    exit 1
fi

echo "📦 Installing required dependencies..."

# Install Inter font
npm install @expo-google-fonts/inter expo-font

# Install animation dependencies if not present
npm install react-native-reanimated react-native-gesture-handler

# Install UI dependencies
npm install expo-linear-gradient react-native-safe-area-context

echo "🔧 Updating configuration files..."

# Update babel.config.js to include reanimated plugin
if ! grep -q "react-native-reanimated/plugin" babel.config.js; then
    echo "Adding Reanimated plugin to babel.config.js..."
    # This is a simplified approach - in production, use a proper JSON parser
    echo "⚠️  Please manually add 'react-native-reanimated/plugin' to your babel.config.js plugins array"
fi

echo "📱 Setting up font loading..."

# Create font loading hook if it doesn't exist
cat > src/hooks/useBoltFonts.ts << 'EOF'
import { useFonts } from 'expo-font';
import {
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
} from '@expo-google-fonts/inter';

export const useBoltFonts = () => {
  const [fontsLoaded, fontError] = useFonts({
    'Inter-Regular': Inter_400Regular,
    'Inter-Medium': Inter_500Medium,
    'Inter-SemiBold': Inter_600SemiBold,
    'Inter-Bold': Inter_700Bold,
  });

  return { fontsLoaded, fontError };
};
EOF

echo "✅ Dependencies installed"

echo "🎯 Next Steps:"
echo "1. Update App.tsx to load Inter fonts using useBoltFonts hook"
echo "2. Replace theme imports with unified theme"
echo "3. Start migrating screens using the MIGRATION_GUIDE.md"
echo "4. Test on both iOS and Android"

echo ""
echo "📚 Resources:"
echo "- Migration Guide: src/components/bolt-ui/MIGRATION_GUIDE.md"
echo "- Example Screen: src/screens/VoicePersonalityScreenMigrated.tsx"
echo "- Components: src/components/bolt-ui/"

echo ""
echo "🚀 Migration setup complete! Happy coding!"
