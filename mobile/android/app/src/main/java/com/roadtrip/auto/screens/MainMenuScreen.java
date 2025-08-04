package com.roadtrip.auto.screens;

import androidx.annotation.NonNull;
import androidx.car.app.CarContext;
import androidx.car.app.Screen;
import androidx.car.app.model.Action;
import androidx.car.app.model.ActionStrip;
import androidx.car.app.model.CarIcon;
import androidx.car.app.model.GridItem;
import androidx.car.app.model.GridTemplate;
import androidx.car.app.model.ItemList;
import androidx.car.app.model.Row;
import androidx.car.app.model.Template;
import androidx.core.graphics.drawable.IconCompat;

import com.roadtrip.auto.R;
import com.roadtrip.auto.RoadTripSession;

/**
 * Main menu screen for Android Auto
 * Displays primary app functions in a grid layout
 */
public class MainMenuScreen extends Screen {
    
    public MainMenuScreen(@NonNull CarContext carContext) {
        super(carContext);
    }
    
    @NonNull
    @Override
    public Template onGetTemplate() {
        ItemList.Builder itemListBuilder = new ItemList.Builder();
        
        // Navigate item
        itemListBuilder.addItem(
            new GridItem.Builder()
                .setTitle("Navigate")
                .setText("Start your journey")
                .setImage(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_navigation))
                    .build())
                .setOnClickListener(() -> onNavigateClick())
                .build());
        
        // Voice Command item
        itemListBuilder.addItem(
            new GridItem.Builder()
                .setTitle("Voice Command")
                .setText("Say a command")
                .setImage(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_mic))
                    .build())
                .setOnClickListener(() -> onVoiceClick())
                .build());
        
        // Games item
        itemListBuilder.addItem(
            new GridItem.Builder()
                .setTitle("Games")
                .setText("Road trip entertainment")
                .setImage(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_games))
                    .build())
                .setOnClickListener(() -> onGamesClick())
                .build());
        
        // Stories item
        itemListBuilder.addItem(
            new GridItem.Builder()
                .setTitle("Stories")
                .setText("Location-based tales")
                .setImage(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_book))
                    .build())
                .setOnClickListener(() -> onStoriesClick())
                .build());
        
        // Recent Trips item
        itemListBuilder.addItem(
            new GridItem.Builder()
                .setTitle("Recent Trips")
                .setText("Your travel history")
                .setImage(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_history))
                    .build())
                .setOnClickListener(() -> onRecentTripsClick())
                .build());
        
        // Settings item
        itemListBuilder.addItem(
            new GridItem.Builder()
                .setTitle("Settings")
                .setText("Customize your experience")
                .setImage(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_settings))
                    .build())
                .setOnClickListener(() -> onSettingsClick())
                .build());
        
        // Create grid template
        GridTemplate.Builder templateBuilder = new GridTemplate.Builder()
            .setTitle("AI Road Trip Storyteller")
            .setHeaderAction(Action.APP_ICON)
            .setSingleList(itemListBuilder.build());
        
        // Add action strip
        ActionStrip.Builder actionStripBuilder = new ActionStrip.Builder();
        
        // Add voice activation button
        actionStripBuilder.addAction(
            new Action.Builder()
                .setIcon(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_mic))
                    .build())
                .setOnClickListener(() -> startVoiceCommand())
                .build());
        
        templateBuilder.setActionStrip(actionStripBuilder.build());
        
        return templateBuilder.build();
    }
    
    /**
     * Handle navigation click
     */
    private void onNavigateClick() {
        // Show search screen or voice input
        getScreenManager().push(new SearchDestinationScreen(getCarContext()));
    }
    
    /**
     * Handle voice command click
     */
    private void onVoiceClick() {
        startVoiceCommand();
    }
    
    /**
     * Handle games click
     */
    private void onGamesClick() {
        getScreenManager().push(new GamesMenuScreen(getCarContext(), null));
    }
    
    /**
     * Handle stories click
     */
    private void onStoriesClick() {
        getScreenManager().push(new StoriesScreen(getCarContext()));
    }
    
    /**
     * Handle recent trips click
     */
    private void onRecentTripsClick() {
        getScreenManager().push(new RecentTripsScreen(getCarContext()));
    }
    
    /**
     * Handle settings click
     */
    private void onSettingsClick() {
        getScreenManager().push(new SettingsScreen(getCarContext()));
    }
    
    /**
     * Start voice command
     */
    private void startVoiceCommand() {
        // Show voice screen
        getScreenManager().push(new VoiceScreen(getCarContext()));
        
        // Or directly start listening
        RoadTripSession session = (RoadTripSession) getCarContext().getCarService(Session.class);
        if (session != null) {
            session.handleVoiceCommand(""); // Start listening
        }
    }
}
