package com.roadtrip.auto;

import android.content.Intent;
import android.content.pm.ApplicationInfo;
import androidx.annotation.NonNull;
import androidx.car.app.CarAppService;
import androidx.car.app.Session;
import androidx.car.app.SessionInfo;
import androidx.car.app.validation.HostValidator;

/**
 * Android Auto Car App Service
 * Entry point for Android Auto integration
 */
public class RoadTripCarAppService extends CarAppService {
    
    @Override
    @NonNull
    public HostValidator createHostValidator() {
        // Allow connections from Android Auto hosts
        if ((getApplicationInfo().flags & ApplicationInfo.FLAG_DEBUGGABLE) != 0) {
            // Allow any host in debug builds
            return HostValidator.ALLOW_ALL_HOSTS_VALIDATOR;
        } else {
            // Only allow official Android Auto hosts in production
            return new HostValidator.Builder(getApplicationContext())
                .addAllowedHosts(androidx.car.app.R.array.hosts_allowlist_sample)
                .build();
        }
    }

    @Override
    @NonNull
    public Session onCreateSession(@NonNull SessionInfo sessionInfo) {
        // Create and return the main session
        return new RoadTripSession();
    }
}
