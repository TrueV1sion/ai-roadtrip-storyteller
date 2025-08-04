package com.roadtrip.auto.screens;

import android.location.Location;
import android.text.SpannableString;
import android.text.Spanned;
import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.car.app.CarContext;
import androidx.car.app.Screen;
import androidx.car.app.constraints.ConstraintManager;
import androidx.car.app.model.Action;
import androidx.car.app.model.ActionStrip;
import androidx.car.app.model.CarIcon;
import androidx.car.app.model.Distance;
import androidx.car.app.model.Template;
import androidx.car.app.navigation.model.Destination;
import androidx.car.app.navigation.model.Lane;
import androidx.car.app.navigation.model.LaneDirection;
import androidx.car.app.navigation.model.Maneuver;
import androidx.car.app.navigation.model.MessageInfo;
import androidx.car.app.navigation.model.NavigationTemplate;
import androidx.car.app.navigation.model.RoutingInfo;
import androidx.car.app.navigation.model.Step;
import androidx.car.app.navigation.model.TravelEstimate;
import androidx.core.graphics.drawable.IconCompat;

import com.roadtrip.auto.R;
import com.roadtrip.auto.managers.NavigationManager;
import com.roadtrip.auto.models.NavigationState;
import com.roadtrip.auto.models.RouteManeuver;

import java.time.Duration;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Navigation screen for Android Auto
 * Displays turn-by-turn navigation with voice guidance
 */
public class NavigationScreen extends Screen implements NavigationManager.NavigationListener {
    
    private final NavigationManager navigationManager;
    private final String destination;
    private NavigationState currentState;
    private boolean isNavigating = false;
    private boolean voiceGuidanceEnabled = true;
    
    public NavigationScreen(@NonNull CarContext carContext, @Nullable String destination) {
        super(carContext);
        this.navigationManager = NavigationManager.getInstance(carContext);
        this.destination = destination;
    }
    
    @Override
    public void onCreate(@NonNull LifecycleOwner owner) {
        super.onCreate(owner);
        
        // Register navigation listener
        navigationManager.addNavigationListener(this);
        
        // Start navigation if destination provided
        if (destination != null) {
            startNavigation();
        } else if (navigationManager.hasActiveNavigation()) {
            // Resume existing navigation
            isNavigating = true;
            currentState = navigationManager.getCurrentState();
        }
    }
    
    @Override
    public void onDestroy(@NonNull LifecycleOwner owner) {
        // Unregister listener
        navigationManager.removeNavigationListener(this);
        super.onDestroy(owner);
    }
    
    @NonNull
    @Override
    public Template onGetTemplate() {
        NavigationTemplate.Builder builder = new NavigationTemplate.Builder();
        
        // Set action strip
        builder.setActionStrip(createActionStrip());
        
        // Set navigation info if navigating
        if (isNavigating && currentState != null) {
            builder.setNavigationInfo(createRoutingInfo());
            
            // Set destination info
            if (currentState.getDestination() != null) {
                builder.setDestinationTravelEstimate(createTravelEstimate());
            }
            
            // Set background color based on severity
            if (currentState.isApproachingManeuver()) {
                builder.setBackgroundColor(CarColor.BLUE);
            }
        } else {
            // Show loading or search message
            builder.setNavigationInfo(createLoadingInfo());
        }
        
        // Enable map action strip
        builder.setMapActionStrip(createMapActionStrip());
        
        return builder.build();
    }
    
    /**
     * Create action strip with navigation controls
     */
    private ActionStrip createActionStrip() {
        ActionStrip.Builder builder = new ActionStrip.Builder();
        
        // Voice toggle
        builder.addAction(
            new Action.Builder()
                .setIcon(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), 
                        voiceGuidanceEnabled ? R.drawable.ic_volume_on : R.drawable.ic_volume_off))
                    .build())
                .setOnClickListener(() -> toggleVoiceGuidance())
                .build());
        
        // Story mode
        builder.addAction(
            new Action.Builder()
                .setIcon(new CarIcon.Builder(
                    IconCompat.createWithResource(getCarContext(), R.drawable.ic_book))
                    .build())
                .setOnClickListener(() -> toggleStoryMode())
                .build());
        
        // End navigation (if active)
        if (isNavigating) {
            builder.addAction(
                new Action.Builder()
                    .setIcon(new CarIcon.Builder(
                        IconCompat.createWithResource(getCarContext(), R.drawable.ic_close))
                        .build())
                    .setOnClickListener(() -> endNavigation())
                    .build());
        }
        
        return builder.build();
    }
    
    /**
     * Create map action strip
     */
    private ActionStrip createMapActionStrip() {
        ActionStrip.Builder builder = new ActionStrip.Builder();
        
        // Center on location
        builder.addAction(
            Action.PAN
                .toBuilder()
                .setOnClickListener(() -> navigationManager.centerOnCurrentLocation())
                .build());
        
        // Zoom controls (if supported)
        int maxActions = getCarContext().getCarService(ConstraintManager.class)
            .getContentLimit(ConstraintManager.CONTENT_LIMIT_TYPE_MAP_ACTION_STRIP);
            
        if (maxActions >= 3) {
            builder.addAction(
                new Action.Builder()
                    .setIcon(new CarIcon.Builder(
                        IconCompat.createWithResource(getCarContext(), R.drawable.ic_zoom_in))
                        .build())
                    .setOnClickListener(() -> navigationManager.zoomIn())
                    .build());
                    
            builder.addAction(
                new Action.Builder()
                    .setIcon(new CarIcon.Builder(
                        IconCompat.createWithResource(getCarContext(), R.drawable.ic_zoom_out))
                        .build())
                    .setOnClickListener(() -> navigationManager.zoomOut())
                    .build());
        }
        
        return builder.build();
    }
    
    /**
     * Create routing info for current maneuver
     */
    private RoutingInfo createRoutingInfo() {
        if (currentState == null || currentState.getCurrentManeuver() == null) {
            return null;
        }
        
        RouteManeuver maneuver = currentState.getCurrentManeuver();
        RoutingInfo.Builder builder = new RoutingInfo.Builder();
        
        // Create current step
        Step.Builder stepBuilder = new Step.Builder(maneuver.getInstruction());
        
        // Set maneuver
        stepBuilder.setManeuver(createManeuver(maneuver));
        
        // Set distance
        stepBuilder.setRoad(maneuver.getRoadName());
        
        // Add lanes if available
        if (maneuver.getLanes() != null && !maneuver.getLanes().isEmpty()) {
            stepBuilder.addLane(createLanes(maneuver.getLanes()));
        }
        
        builder.setCurrentStep(stepBuilder.build(), 
            Distance.create(maneuver.getDistanceMeters(), Distance.UNIT_METERS));
        
        // Set next step if available
        if (currentState.getNextManeuver() != null) {
            RouteManeuver nextManeuver = currentState.getNextManeuver();
            builder.setNextStep(
                new Step.Builder(nextManeuver.getInstruction())
                    .setManeuver(createManeuver(nextManeuver))
                    .build());
        }
        
        // Set loading state
        builder.setLoading(false);
        
        return builder.build();
    }
    
    /**
     * Create maneuver icon
     */
    private Maneuver createManeuver(RouteManeuver routeManeuver) {
        Maneuver.Builder builder = new Maneuver.Builder(getManeuverType(routeManeuver.getType()));
        
        // Set roundabout info if applicable
        if (routeManeuver.getRoundaboutExitNumber() > 0) {
            builder.setRoundaboutExitNumber(routeManeuver.getRoundaboutExitNumber());
        }
        
        // Set icon
        builder.setIcon(new CarIcon.Builder(
            IconCompat.createWithResource(getCarContext(), getManeuverIcon(routeManeuver.getType())))
            .build());
        
        return builder.build();
    }
    
    /**
     * Create lanes
     */
    private Lane createLanes(List<RouteManeuver.LaneInfo> laneInfos) {
        Lane.Builder builder = new Lane.Builder();
        
        for (RouteManeuver.LaneInfo laneInfo : laneInfos) {
            LaneDirection.Builder dirBuilder = new LaneDirection.Builder();
            
            if (laneInfo.isStraight()) {
                dirBuilder.setShape(LaneDirection.SHAPE_STRAIGHT);
            } else if (laneInfo.isLeft()) {
                dirBuilder.setShape(LaneDirection.SHAPE_SHARP_LEFT);
            } else if (laneInfo.isRight()) {
                dirBuilder.setShape(LaneDirection.SHAPE_SHARP_RIGHT);
            }
            
            dirBuilder.setHighlighted(laneInfo.isRecommended());
            builder.addDirection(dirBuilder.build());
        }
        
        return builder.build();
    }
    
    /**
     * Create travel estimate
     */
    private TravelEstimate createTravelEstimate() {
        if (currentState == null) {
            return null;
        }
        
        TravelEstimate.Builder builder = new TravelEstimate.Builder(
            Distance.create(currentState.getRemainingDistanceMeters(), Distance.UNIT_METERS),
            Duration.ofSeconds(currentState.getRemainingTimeSeconds()),
            ZonedDateTime.now().plusSeconds(currentState.getRemainingTimeSeconds()));
        
        // Set color based on traffic
        if (currentState.hasHeavyTraffic()) {
            builder.setRemainingTimeColor(CarColor.RED);
        } else if (currentState.hasModerateTraffic()) {
            builder.setRemainingTimeColor(CarColor.YELLOW);
        } else {
            builder.setRemainingTimeColor(CarColor.GREEN);
        }
        
        return builder.build();
    }
    
    /**
     * Create loading info
     */
    private RoutingInfo createLoadingInfo() {
        return new RoutingInfo.Builder()
            .setLoading(true)
            .build();
    }
    
    /**
     * Start navigation
     */
    private void startNavigation() {
        navigationManager.startNavigation(destination, new NavigationManager.NavigationCallback() {
            @Override
            public void onSuccess() {
                isNavigating = true;
                invalidate();
            }
            
            @Override
            public void onError(String error) {
                getCarContext().showToast(error, CarContext.DURATION_LONG);
                getScreenManager().pop();
            }
        });
    }
    
    /**
     * End navigation
     */
    private void endNavigation() {
        navigationManager.stopNavigation();
        getScreenManager().pop();
    }
    
    /**
     * Toggle voice guidance
     */
    private void toggleVoiceGuidance() {
        voiceGuidanceEnabled = !voiceGuidanceEnabled;
        navigationManager.setVoiceGuidanceEnabled(voiceGuidanceEnabled);
        invalidate();
    }
    
    /**
     * Toggle story mode
     */
    private void toggleStoryMode() {
        boolean enabled = navigationManager.toggleStoryMode();
        getCarContext().showToast(
            enabled ? "Story mode enabled" : "Story mode disabled",
            CarContext.DURATION_SHORT);
    }
    
    // NavigationListener implementation
    
    @Override
    public void onNavigationStateChanged(NavigationState state) {
        currentState = state;
        invalidate();
    }
    
    @Override
    public void onManeuverApproaching(RouteManeuver maneuver) {
        // Voice announcement handled by NavigationManager
        invalidate();
    }
    
    @Override
    public void onArrival() {
        getCarContext().showToast("You have arrived!", CarContext.DURATION_LONG);
        getScreenManager().pop();
    }
    
    @Override
    public void onRerouting() {
        getCarContext().showToast("Recalculating route...", CarContext.DURATION_SHORT);
    }
    
    // Helper methods
    
    private int getManeuverType(String type) {
        switch (type) {
            case "turn_left":
                return Maneuver.TYPE_TURN_LEFT;
            case "turn_right":
                return Maneuver.TYPE_TURN_RIGHT;
            case "straight":
                return Maneuver.TYPE_STRAIGHT;
            case "u_turn":
                return Maneuver.TYPE_U_TURN_LEFT;
            case "roundabout":
                return Maneuver.TYPE_ROUNDABOUT_ENTER;
            case "merge":
                return Maneuver.TYPE_MERGE_LEFT;
            case "exit":
                return Maneuver.TYPE_OFF_RAMP_NORMAL_RIGHT;
            default:
                return Maneuver.TYPE_UNKNOWN;
        }
    }
    
    private int getManeuverIcon(String type) {
        switch (type) {
            case "turn_left":
                return R.drawable.ic_turn_left;
            case "turn_right":
                return R.drawable.ic_turn_right;
            case "straight":
                return R.drawable.ic_straight;
            case "u_turn":
                return R.drawable.ic_u_turn;
            case "roundabout":
                return R.drawable.ic_roundabout;
            case "merge":
                return R.drawable.ic_merge;
            case "exit":
                return R.drawable.ic_exit;
            default:
                return R.drawable.ic_navigation;
        }
    }
}
