import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';

import ARScreen from '../screens/ARScreen';
import { MainNavigator } from './MainNavigator';

export type ARStackParamList = {
  Main: undefined;
  ARScreen: {
    mode?: 'historical' | 'navigation' | 'nature' | 'all';
    latitude?: number;
    longitude?: number;
    radius?: number;
    year?: number;
  };
};

const Stack = createStackNavigator<ARStackParamList>();

export const ARNavigator: React.FC = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        presentation: 'modal',
        gestureEnabled: false
      }}
    >
      <Stack.Screen name="Main" component={MainNavigator} />
      <Stack.Screen 
        name="ARScreen" 
        component={ARScreen}
        options={{
          cardStyle: { backgroundColor: 'transparent' }
        }}
      />
    </Stack.Navigator>
  );
};

export default ARNavigator;