package com.roadtrip.auto.managers;

import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;
import androidx.annotation.NonNull;
import androidx.car.app.CarContext;
import androidx.car.app.CarToast;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Voice Manager for Android Auto
 * Handles voice recognition and text-to-speech
 */
public class VoiceManager implements RecognitionListener, TextToSpeech.OnInitListener {
    
    private static final String TAG = "VoiceManager";
    private static VoiceManager instance;
    
    private final CarContext carContext;
    private SpeechRecognizer speechRecognizer;
    private TextToSpeech textToSpeech;
    private boolean isListening = false;
    private boolean isSpeaking = false;
    private boolean isInitialized = false;
    private String currentPersonality = "friendly_guide";
    private CommandCallback currentCallback;
    
    // Voice personalities
    private static final Map<String, VoicePersonality> PERSONALITIES = new HashMap<>();
    static {
        PERSONALITIES.put("friendly_guide", new VoicePersonality(
            "Friendly Guide", 1.0f, 1.0f, "I'll be your friendly guide today!"));
        PERSONALITIES.put("morgan_freeman", new VoicePersonality(
            "Morgan Freeman", 0.9f, 0.8f, "Let me narrate your journey."));
        PERSONALITIES.put("david_attenborough", new VoicePersonality(
            "David Attenborough", 0.95f, 0.9f, "The natural world awaits us."));
        PERSONALITIES.put("enthusiastic_explorer", new VoicePersonality(
            "Enthusiastic Explorer", 1.1f, 1.2f, "This is going to be amazing!"));
        PERSONALITIES.put("calm_companion", new VoicePersonality(
            "Calm Companion", 0.85f, 0.9f, "Let's enjoy a peaceful journey."));
    }
    
    // Command patterns
    private static final Pattern NAVIGATE_PATTERN = Pattern.compile(
        "(navigate|go|drive|take me) to (.+)", Pattern.CASE_INSENSITIVE);
    private static final Pattern GAME_PATTERN = Pattern.compile(
        "(play|start) (trivia|twenty questions|bingo)", Pattern.CASE_INSENSITIVE);
    private static final Pattern STORY_PATTERN = Pattern.compile(
        "(tell|play) (me )?a story", Pattern.CASE_INSENSITIVE);
    private static final Pattern VOICE_PATTERN = Pattern.compile(
        "change voice to (.+)", Pattern.CASE_INSENSITIVE);
    
    private VoiceManager(CarContext carContext) {
        this.carContext = carContext;
    }
    
    public static VoiceManager getInstance(CarContext carContext) {
        if (instance == null) {
            instance = new VoiceManager(carContext);
        }
        return instance;
    }
    
    /**
     * Initialize voice services
     */
    public void initialize() {
        // Initialize speech recognizer
        if (SpeechRecognizer.isRecognitionAvailable(carContext)) {
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(carContext);
            speechRecognizer.setRecognitionListener(this);
        } else {
            Log.w(TAG, "Speech recognition not available");
        }
        
        // Initialize text-to-speech
        textToSpeech = new TextToSpeech(carContext, this);
        textToSpeech.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override
            public void onStart(String utteranceId) {
                isSpeaking = true;
            }
            
            @Override
            public void onDone(String utteranceId) {
                isSpeaking = false;
                // Resume listening if it was active
                if (isListening) {
                    startListening();
                }
            }
            
            @Override
            public void onError(String utteranceId) {
                isSpeaking = false;
            }
        });
    }
    
    /**
     * Start listening for voice commands
     */
    public void startListening() {
        if (!isInitialized || speechRecognizer == null || isSpeaking) {
            return;
        }
        
        if (isListening) {
            stopListening();
        }
        
        Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault());
        intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
        intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
        
        isListening = true;
        speechRecognizer.startListening(intent);
    }
    
    /**
     * Stop listening
     */
    public void stopListening() {
        if (speechRecognizer != null) {
            isListening = false;
            speechRecognizer.stopListening();
        }
    }
    
    /**
     * Process voice command
     */
    public void processCommand(String command, CommandCallback callback) {
        this.currentCallback = callback;
        
        // Navigation command
        Matcher navMatcher = NAVIGATE_PATTERN.matcher(command);
        if (navMatcher.find()) {
            String destination = navMatcher.group(2);
            speak("Navigating to " + destination);
            if (callback != null) {
                callback.onNavigate(destination);
            }
            return;
        }
        
        // Game command
        Matcher gameMatcher = GAME_PATTERN.matcher(command);
        if (gameMatcher.find()) {
            String gameType = gameMatcher.group(2).toLowerCase();
            speak("Starting " + gameType);
            if (callback != null) {
                callback.onStartGame(gameType);
            }
            return;
        }
        
        // Story command
        Matcher storyMatcher = STORY_PATTERN.matcher(command);
        if (storyMatcher.find()) {
            speak("I'll tell you a story");
            if (callback != null) {
                callback.onPlayStory();
            }
            return;
        }
        
        // Voice change command
        Matcher voiceMatcher = VOICE_PATTERN.matcher(command);
        if (voiceMatcher.find()) {
            String voiceName = voiceMatcher.group(1).toLowerCase();
            for (Map.Entry<String, VoicePersonality> entry : PERSONALITIES.entrySet()) {
                if (entry.getValue().name.toLowerCase().contains(voiceName)) {
                    setPersonality(entry.getKey());
                    speak(entry.getValue().greeting);
                    return;
                }
            }
        }
        
        // Common navigation commands
        if (command.toLowerCase().contains("go home")) {
            speak("Taking you home");
            if (callback != null) {
                callback.onNavigate("home");
            }
            return;
        }
        
        if (command.toLowerCase().contains("gas station") || 
            command.toLowerCase().contains("fuel")) {
            speak("Finding nearby gas stations");
            if (callback != null) {
                callback.onNavigate("gas station");
            }
            return;
        }
        
        if (command.toLowerCase().contains("restaurant") || 
            command.toLowerCase().contains("food")) {
            speak("Finding restaurants nearby");
            if (callback != null) {
                callback.onNavigate("restaurant");
            }
            return;
        }
        
        if (command.toLowerCase().contains("settings")) {
            if (callback != null) {
                callback.onOpenSettings();
            }
            return;
        }
        
        // Unknown command
        speak("I didn't understand that. Try saying 'navigate to' followed by a destination.");
        if (callback != null) {
            callback.onError("Command not recognized");
        }
    }
    
    /**
     * Speak text with current personality
     */
    public void speak(String text) {
        if (textToSpeech == null || !isInitialized) {
            return;
        }
        
        // Stop current speech
        if (isSpeaking) {
            textToSpeech.stop();
        }
        
        // Apply personality settings
        VoicePersonality personality = PERSONALITIES.get(currentPersonality);
        if (personality != null) {
            textToSpeech.setSpeechRate(personality.speechRate);
            textToSpeech.setPitch(personality.pitch);
        }
        
        // Speak
        HashMap<String, String> params = new HashMap<>();
        params.put(TextToSpeech.Engine.KEY_PARAM_UTTERANCE_ID, String.valueOf(System.currentTimeMillis()));
        textToSpeech.speak(text, TextToSpeech.QUEUE_FLUSH, params);
    }
    
    /**
     * Announce navigation instruction
     */
    public void announceNavigation(String instruction, int distanceMeters) {
        String announcement;
        if (distanceMeters < 100) {
            announcement = instruction + " now";
        } else if (distanceMeters < 500) {
            announcement = "In " + distanceMeters + " meters, " + instruction;
        } else {
            int km = distanceMeters / 1000;
            announcement = "In " + km + " kilometers, " + instruction;
        }
        
        speak(announcement);
    }
    
    /**
     * Set voice personality
     */
    public void setPersonality(String personalityId) {
        if (PERSONALITIES.containsKey(personalityId)) {
            this.currentPersonality = personalityId;
        }
    }
    
    /**
     * Get current personality
     */
    public String getCurrentPersonality() {
        return currentPersonality;
    }
    
    /**
     * Get available personalities
     */
    public Map<String, String> getAvailablePersonalities() {
        Map<String, String> result = new HashMap<>();
        for (Map.Entry<String, VoicePersonality> entry : PERSONALITIES.entrySet()) {
            result.put(entry.getKey(), entry.getValue().name);
        }
        return result;
    }
    
    /**
     * Cleanup resources
     */
    public void cleanup() {
        if (speechRecognizer != null) {
            speechRecognizer.destroy();
            speechRecognizer = null;
        }
        
        if (textToSpeech != null) {
            textToSpeech.stop();
            textToSpeech.shutdown();
            textToSpeech = null;
        }
        
        isInitialized = false;
    }
    
    // TextToSpeech.OnInitListener
    
    @Override
    public void onInit(int status) {
        if (status == TextToSpeech.SUCCESS) {
            int result = textToSpeech.setLanguage(Locale.getDefault());
            if (result == TextToSpeech.LANG_MISSING_DATA ||
                result == TextToSpeech.LANG_NOT_SUPPORTED) {
                Log.e(TAG, "Language not supported");
            } else {
                isInitialized = true;
                // Set initial personality
                VoicePersonality personality = PERSONALITIES.get(currentPersonality);
                if (personality != null) {
                    textToSpeech.setSpeechRate(personality.speechRate);
                    textToSpeech.setPitch(personality.pitch);
                }
            }
        } else {
            Log.e(TAG, "TTS initialization failed");
        }
    }
    
    // RecognitionListener implementation
    
    @Override
    public void onReadyForSpeech(Bundle params) {
        // Ready to listen
    }
    
    @Override
    public void onBeginningOfSpeech() {
        // User started speaking
    }
    
    @Override
    public void onRmsChanged(float rmsdB) {
        // Volume changed
    }
    
    @Override
    public void onBufferReceived(byte[] buffer) {
        // Audio buffer received
    }
    
    @Override
    public void onEndOfSpeech() {
        // User stopped speaking
    }
    
    @Override
    public void onError(int error) {
        Log.e(TAG, "Speech recognition error: " + error);
        isListening = false;
        
        // Restart listening if it was a recoverable error
        if (error == SpeechRecognizer.ERROR_NO_MATCH ||
            error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) {
            startListening();
        }
    }
    
    @Override
    public void onResults(Bundle results) {
        ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if (matches != null && !matches.isEmpty()) {
            String command = matches.get(0);
            Log.d(TAG, "Recognized: " + command);
            processCommand(command, currentCallback);
        }
        
        // Continue listening
        if (isListening) {
            startListening();
        }
    }
    
    @Override
    public void onPartialResults(Bundle partialResults) {
        // Handle partial results if needed
    }
    
    @Override
    public void onEvent(int eventType, Bundle params) {
        // Handle events
    }
    
    /**
     * Voice personality configuration
     */
    private static class VoicePersonality {
        final String name;
        final float speechRate;
        final float pitch;
        final String greeting;
        
        VoicePersonality(String name, float speechRate, float pitch, String greeting) {
            this.name = name;
            this.speechRate = speechRate;
            this.pitch = pitch;
            this.greeting = greeting;
        }
    }
    
    /**
     * Command callback interface
     */
    public interface CommandCallback {
        void onNavigate(String destination);
        void onPlayStory();
        void onStartGame(String gameType);
        void onOpenSettings();
        void onError(String error);
    }
}
