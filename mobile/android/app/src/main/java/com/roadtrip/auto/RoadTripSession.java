package com.roadtrip.auto;

import android.content.Intent;
import android.text.TextUtils;
import androidx.annotation.NonNull;
import androidx.car.app.CarContext;
import androidx.car.app.Screen;
import androidx.car.app.ScreenManager;
import androidx.car.app.Session;
import androidx.lifecycle.DefaultLifecycleObserver;
import androidx.lifecycle.LifecycleOwner;

import com.roadtrip.auto.screens.NavigationScreen;
import com.roadtrip.auto.screens.MainMenuScreen;
import com.roadtrip.auto.screens.VoiceScreen;
import com.roadtrip.auto.screens.GamesMenuScreen;
import com.roadtrip.auto.screens.SettingsScreen;
import com.roadtrip.auto.managers.VoiceManager;
import com.roadtrip.auto.managers.NavigationManager;
import com.roadtrip.auto.managers.StoryManager;

/**
 * Main Android Auto session
 * Manages the lifecycle and screen navigation
 */
public class RoadTripSession extends Session implements DefaultLifecycleObserver {
    
    private VoiceManager voiceManager;
    private NavigationManager navigationManager;
    private StoryManager storyManager;
    private boolean isNavigating = false;
    
    @Override
    public void onCreate(@NonNull LifecycleOwner owner) {
        super.onCreate(owner);
        
        // Initialize managers
        voiceManager = VoiceManager.getInstance(getCarContext());
        navigationManager = NavigationManager.getInstance(getCarContext());
        storyManager = StoryManager.getInstance(getCarContext());
        
        // Setup voice recognition
        voiceManager.initialize();
        
        // Register lifecycle observer
        getLifecycle().addObserver(this);
    }
    
    @Override
    @NonNull
    public Screen onCreateScreen(@NonNull Intent intent) {
        // Check if launched with navigation intent
        if (intent != null && CarContext.ACTION_NAVIGATE.equals(intent.getAction())) {
            // Extract destination from intent
            String query = intent.getStringExtra(CarContext.EXTRA_QUERY_PLAIN_TEXT);
            if (!TextUtils.isEmpty(query)) {
                // Start navigation directly
                return new NavigationScreen(getCarContext(), query);
            }
        }
        
        // Check if we have an active navigation session
        if (navigationManager.hasActiveNavigation()) {
            return new NavigationScreen(getCarContext(), null);
        }
        
        // Default to main menu
        return new MainMenuScreen(getCarContext());
    }
    
    @Override
    public void onNewIntent(@NonNull Intent intent) {
        super.onNewIntent(intent);
        
        // Handle new navigation requests
        if (CarContext.ACTION_NAVIGATE.equals(intent.getAction())) {
            String query = intent.getStringExtra(CarContext.EXTRA_QUERY_PLAIN_TEXT);
            if (!TextUtils.isEmpty(query)) {
                // Navigate to navigation screen
                ScreenManager screenManager = getCarContext().getCarService(ScreenManager.class);
                screenManager.push(new NavigationScreen(getCarContext(), query));
            }
        }
    }
    
    @Override
    public void onCarConfigurationChanged(@NonNull android.content.res.Configuration configuration) {
        // Handle configuration changes (dark mode, etc.)
        if (configuration.uiMode != getCarContext().getResources().getConfiguration().uiMode) {
            // Refresh current screen for theme changes
            ScreenManager screenManager = getCarContext().getCarService(ScreenManager.class);
            Screen currentScreen = screenManager.getTop();
            if (currentScreen != null) {
                currentScreen.invalidate();
            }
        }
    }
    
    @Override
    public void onStart(@NonNull LifecycleOwner owner) {
        // Resume voice recognition
        voiceManager.startListening();
        
        // Resume story playback if active
        if (storyManager.isPaused()) {
            storyManager.resume();
        }
    }
    
    @Override
    public void onStop(@NonNull LifecycleOwner owner) {
        // Pause voice recognition
        voiceManager.stopListening();
        
        // Pause story playback
        if (storyManager.isPlaying()) {
            storyManager.pause();
        }
    }
    
    @Override
    public void onDestroy(@NonNull LifecycleOwner owner) {
        // Cleanup resources
        voiceManager.cleanup();
        navigationManager.cleanup();
        storyManager.cleanup();
        
        super.onDestroy(owner);
    }
    
    /**
     * Handle voice commands from any screen
     */
    public void handleVoiceCommand(String command) {
        // Process through voice manager
        voiceManager.processCommand(command, new VoiceManager.CommandCallback() {
            @Override
            public void onNavigate(String destination) {
                // Push navigation screen
                ScreenManager screenManager = getCarContext().getCarService(ScreenManager.class);
                screenManager.push(new NavigationScreen(getCarContext(), destination));
            }
            
            @Override
            public void onPlayStory() {
                storyManager.playNextStory();
            }
            
            @Override
            public void onStartGame(String gameType) {
                // Push game screen
                ScreenManager screenManager = getCarContext().getCarService(ScreenManager.class);
                screenManager.push(new GamesMenuScreen(getCarContext(), gameType));
            }
            
            @Override
            public void onOpenSettings() {
                // Push settings screen
                ScreenManager screenManager = getCarContext().getCarService(ScreenManager.class);
                screenManager.push(new SettingsScreen(getCarContext()));
            }
            
            @Override
            public void onError(String error) {
                // Show error toast
                getCarContext().showToast(error, CarContext.DURATION_SHORT);
            }
        });
    }
    
    /**
     * Check if navigation is active
     */
    public boolean isNavigating() {
        return navigationManager.hasActiveNavigation();
    }
    
    /**
     * Get current voice personality
     */
    public String getCurrentVoicePersonality() {
        return voiceManager.getCurrentPersonality();
    }
    
    /**
     * Set voice personality
     */
    public void setVoicePersonality(String personality) {
        voiceManager.setPersonality(personality);
    }
}
