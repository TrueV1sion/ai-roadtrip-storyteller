/**
 * State Management Adapter
 * Bridges the gap between Bolt's Zustand patterns and RoadTrip's Redux
 */

import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../../store';
import { useCallback } from 'react';

/**
 * Hook that provides Zustand-like API for Redux state
 * Makes it easier to migrate Bolt components
 */
export function useStoreAdapter<T>(
  selector: (state: RootState) => T,
  actions?: Record<string, (...args: any[]) => any>
) {
  const dispatch = useDispatch();
  const state = useSelector(selector);
  
  // Wrap actions to auto-dispatch
  const wrappedActions = useCallback(() => {
    if (!actions) return {};
    
    const wrapped: Record<string, (...args: any[]) => void> = {};
    
    Object.keys(actions).forEach(key => {
      wrapped[key] = (...args: any[]) => {
        dispatch(actions[key](...args));
      };
    });
    
    return wrapped;
  }, [dispatch, actions]);
  
  return {
    state,
    ...wrappedActions(),
  };
}

/**
 * Example usage for migrating a Bolt component:
 * 
 * // Bolt (Zustand):
 * const { user, login, logout } = useAuthStore();
 * 
 * // RoadTrip (Redux with adapter):
 * const { state: user, login, logout } = useStoreAdapter(
 *   (state) => state.auth.user,
 *   {
 *     login: authActions.login,
 *     logout: authActions.logout,
 *   }
 * );
 */

// Commonly used selectors for Bolt components
export const selectors = {
  // Auth selectors
  auth: {
    user: (state: RootState) => state.auth.user,
    isAuthenticated: (state: RootState) => !!state.auth.user,
    isLoading: (state: RootState) => state.auth.loading,
  },
  
  // Story selectors
  story: {
    currentStory: (state: RootState) => state.story.currentStory,
    isPlaying: (state: RootState) => state.story.isPlaying,
    likedStories: (state: RootState) => state.story.likedStories,
    storyHistory: (state: RootState) => state.story.history,
  },
  
  // Voice personality selectors
  voice: {
    selectedPersonality: (state: RootState) => state.voice.selectedPersonality,
    availablePersonalities: (state: RootState) => state.voice.availablePersonalities,
    autoSelect: (state: RootState) => state.voice.autoSelect,
  },
  
  // Navigation selectors
  navigation: {
    currentRoute: (state: RootState) => state.navigation.currentRoute,
    destination: (state: RootState) => state.navigation.destination,
    waypoints: (state: RootState) => state.navigation.waypoints,
  },
  
  // UI selectors
  ui: {
    theme: (state: RootState) => state.ui.theme,
    isLoading: (state: RootState) => state.ui.isLoading,
    error: (state: RootState) => state.ui.error,
  },
};

// Re-export commonly used hooks with simpler names
export const useAuth = () => useStoreAdapter(
  selectors.auth.user,
  {
    // Add auth actions here
  }
);

export const useStory = () => useStoreAdapter(
  (state) => ({
    currentStory: selectors.story.currentStory(state),
    isPlaying: selectors.story.isPlaying(state),
    likedStories: selectors.story.likedStories(state),
  }),
  {
    // Add story actions here
  }
);

export const useVoicePersonality = () => useStoreAdapter(
  (state) => ({
    selected: selectors.voice.selectedPersonality(state),
    available: selectors.voice.availablePersonalities(state),
    autoSelect: selectors.voice.autoSelect(state),
  }),
  {
    // Add voice actions here
  }
);
