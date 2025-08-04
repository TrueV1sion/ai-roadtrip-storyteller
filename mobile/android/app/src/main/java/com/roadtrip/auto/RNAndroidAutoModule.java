package com.roadtrip.auto;

import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.ServiceConnection;
import android.os.IBinder;
import android.util.Log;

import com.facebook.react.bridge.Arguments;
import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;
import com.facebook.react.bridge.ReadableMap;
import com.facebook.react.bridge.WritableMap;
import com.facebook.react.modules.core.DeviceEventManagerModule;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

/**
 * React Native module for Android Auto integration
 */
public class RNAndroidAutoModule extends ReactContextBaseJavaModule {
    
    private static final String TAG = "RNAndroidAuto";
    private static final String MODULE_NAME = "RNAndroidAuto";
    
    // Event names
    private static final String EVENT_CONNECTED = "androidAutoConnected";
    private static final String EVENT_DISCONNECTED = "androidAutoDisconnected";
    private static final String EVENT_NAVIGATION_STARTED = "navigationStarted";
    private static final String EVENT_NAVIGATION_ENDED = "navigationEnded";
    private static final String EVENT_VOICE_COMMAND = "voiceCommand";
    
    private final ReactApplicationContext reactContext;
    private AndroidAutoConnection autoConnection;
    private boolean isConnected = false;
    
    public RNAndroidAutoModule(ReactApplicationContext reactContext) {
        super(reactContext);
        this.reactContext = reactContext;
    }
    
    @NonNull
    @Override
    public String getName() {
        return MODULE_NAME;
    }
    
    /**
     * Initialize Android Auto connection
     */
    @ReactMethod
    public void initialize(Promise promise) {
        try {
            if (autoConnection == null) {
                autoConnection = new AndroidAutoConnection();
            }
            
            // Check if Android Auto is available
            boolean isAvailable = checkAndroidAutoAvailability();
            
            WritableMap result = Arguments.createMap();
            result.putBoolean("available", isAvailable);
            result.putBoolean("connected", isConnected);
            
            promise.resolve(result);
        } catch (Exception e) {
            promise.reject("INIT_ERROR", "Failed to initialize Android Auto", e);
        }
    }
    
    /**
     * Start navigation
     */
    @ReactMethod
    public void startNavigation(ReadableMap options, Promise promise) {
        try {
            if (!isConnected) {
                promise.reject("NOT_CONNECTED", "Android Auto not connected");
                return;
            }
            
            String destination = options.getString("destination");
            if (destination == null) {
                promise.reject("INVALID_PARAMS", "Destination is required");
                return;
            }
            
            // Send navigation intent to Android Auto
            Intent intent = new Intent("com.roadtrip.auto.NAVIGATE");
            intent.putExtra("destination", destination);
            
            if (options.hasKey("waypoints")) {
                // Add waypoints if provided
                intent.putExtra("waypoints", options.getArray("waypoints").toString());
            }
            
            reactContext.sendBroadcast(intent);
            
            // Send event
            sendEvent(EVENT_NAVIGATION_STARTED, Arguments.createMap());
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("NAV_ERROR", "Failed to start navigation", e);
        }
    }
    
    /**
     * End navigation
     */
    @ReactMethod
    public void endNavigation(Promise promise) {
        try {
            if (!isConnected) {
                promise.reject("NOT_CONNECTED", "Android Auto not connected");
                return;
            }
            
            // Send end navigation intent
            Intent intent = new Intent("com.roadtrip.auto.END_NAVIGATION");
            reactContext.sendBroadcast(intent);
            
            // Send event
            sendEvent(EVENT_NAVIGATION_ENDED, Arguments.createMap());
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("NAV_ERROR", "Failed to end navigation", e);
        }
    }
    
    /**
     * Update navigation maneuver
     */
    @ReactMethod
    public void updateManeuver(ReadableMap maneuver, Promise promise) {
        try {
            if (!isConnected) {
                promise.reject("NOT_CONNECTED", "Android Auto not connected");
                return;
            }
            
            // Send maneuver update
            Intent intent = new Intent("com.roadtrip.auto.UPDATE_MANEUVER");
            intent.putExtra("instruction", maneuver.getString("instruction"));
            intent.putExtra("distance", maneuver.getInt("distance"));
            intent.putExtra("type", maneuver.getString("type"));
            
            reactContext.sendBroadcast(intent);
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("UPDATE_ERROR", "Failed to update maneuver", e);
        }
    }
    
    /**
     * Set voice personality
     */
    @ReactMethod
    public void setVoicePersonality(String personality, Promise promise) {
        try {
            Intent intent = new Intent("com.roadtrip.auto.SET_VOICE");
            intent.putExtra("personality", personality);
            reactContext.sendBroadcast(intent);
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("VOICE_ERROR", "Failed to set voice personality", e);
        }
    }
    
    /**
     * Start voice recognition
     */
    @ReactMethod
    public void startVoiceRecognition(Promise promise) {
        try {
            if (!isConnected) {
                promise.reject("NOT_CONNECTED", "Android Auto not connected");
                return;
            }
            
            Intent intent = new Intent("com.roadtrip.auto.START_VOICE");
            reactContext.sendBroadcast(intent);
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("VOICE_ERROR", "Failed to start voice recognition", e);
        }
    }
    
    /**
     * Play story
     */
    @ReactMethod
    public void playStory(ReadableMap story, Promise promise) {
        try {
            Intent intent = new Intent("com.roadtrip.auto.PLAY_STORY");
            intent.putExtra("title", story.getString("title"));
            intent.putExtra("content", story.getString("content"));
            intent.putExtra("voiceUrl", story.getString("voiceUrl"));
            
            reactContext.sendBroadcast(intent);
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("STORY_ERROR", "Failed to play story", e);
        }
    }
    
    /**
     * Start game
     */
    @ReactMethod
    public void startGame(String gameType, Promise promise) {
        try {
            Intent intent = new Intent("com.roadtrip.auto.START_GAME");
            intent.putExtra("gameType", gameType);
            reactContext.sendBroadcast(intent);
            
            promise.resolve(true);
            
        } catch (Exception e) {
            promise.reject("GAME_ERROR", "Failed to start game", e);
        }
    }
    
    /**
     * Get connection status
     */
    @ReactMethod
    public void getConnectionStatus(Promise promise) {
        WritableMap status = Arguments.createMap();
        status.putBoolean("connected", isConnected);
        status.putBoolean("available", checkAndroidAutoAvailability());
        
        promise.resolve(status);
    }
    
    /**
     * Check if Android Auto is available
     */
    private boolean checkAndroidAutoAvailability() {
        try {
            // Check if Android Auto app is installed
            reactContext.getPackageManager().getPackageInfo(
                "com.google.android.projection.gearhead", 0);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
    
    /**
     * Send event to JavaScript
     */
    private void sendEvent(String eventName, @Nullable WritableMap params) {
        reactContext
            .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter.class)
            .emit(eventName, params);
    }
    
    /**
     * Android Auto connection handler
     */
    private class AndroidAutoConnection implements ServiceConnection {
        
        @Override
        public void onServiceConnected(ComponentName name, IBinder service) {
            Log.d(TAG, "Android Auto connected");
            isConnected = true;
            sendEvent(EVENT_CONNECTED, Arguments.createMap());
        }
        
        @Override
        public void onServiceDisconnected(ComponentName name) {
            Log.d(TAG, "Android Auto disconnected");
            isConnected = false;
            sendEvent(EVENT_DISCONNECTED, Arguments.createMap());
        }
        
        @Override
        public void onBindingDied(ComponentName name) {
            Log.d(TAG, "Android Auto binding died");
            isConnected = false;
            sendEvent(EVENT_DISCONNECTED, Arguments.createMap());
        }
    }
    
    /**
     * Handle voice command result
     */
    public void onVoiceCommand(String command) {
        WritableMap params = Arguments.createMap();
        params.putString("command", command);
        sendEvent(EVENT_VOICE_COMMAND, params);
    }
}
