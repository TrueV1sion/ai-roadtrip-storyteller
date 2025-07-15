# Road Trip App - Google Cloud Integration Plan

This document outlines the implementation plan to fully leverage Google Cloud services for the Road Trip application backend and related components.

## Outstanding Implementation Tasks & Refactoring

1.  **Implement Backend CRUD Operations:**
    *   **Category:** New Feature / Core Implementation
    *   **Description:** Implement the database Create, Read, Update, Delete functions (likely in `backend/app/crud/`) for `User`, `UserPreferences`, and `Story` models. This is essential for data persistence and functionality of routes like `personalized_story`.
    *   **Priority:** High
    *   **Effort:** Large

2.  **Remove Redundant AI Client:**
    *   **Category:** Refactoring / Chore
    *   **Description:** Delete `backend/app/core/google_ai_client.py` and update `backend/app/routes/immersive.py` to remove the fallback logic using this client. Standardize on `ai_client.py` and `enhanced_ai_client.py`.
    *   **Priority:** High
    *   **Effort:** Small

3.  **Configure Database Connection (Cloud SQL):**
    *   **Category:** Infrastructure / Configuration
    *   **Description:** Update application configuration (`backend/app/core/config.py`, `.env`) to connect to the provisioned Google Cloud SQL instance.
    *   **Priority:** High
    *   **Effort:** Small

4.  **Integrate Secrets Management (Google Secret Manager):**
    *   **Category:** Security / Infrastructure
    *   **Description:** Store sensitive data (API keys, DB credentials, JWT secret) in Google Secret Manager and update `backend/app/core/config.py` to fetch them securely.
    *   **Priority:** High
    *   **Effort:** Medium

5.  **Standardize STT Service (Google Speech-to-Text):**
    *   **Category:** Refactoring / Enhancement
    *   **Description:** Review `backend/app/services/stt_service.py`. If not already using Google Cloud Speech-to-Text, migrate it for consistency within the Google Cloud ecosystem.
    *   **Priority:** Medium
    *   **Effort:** Medium

6.  **Refine Dockerfile & CI/CD for Cloud Deployment:**
    *   **Category:** Infrastructure / DevOps
    *   **Description:** Optimize the `Dockerfile` for production builds and enhance the GitHub Actions workflow (`.github/workflows/ci.yml`) for automated testing and deployment to Google Cloud Run or GKE.
    *   **Priority:** Medium
    *   **Effort:** Medium

7.  **Configure Cloud Logging Integration:**
    *   **Category:** Infrastructure / Monitoring
    *   **Description:** Update the logger (`backend/app/core/logger.py`) to output JSON-formatted logs compatible with Google Cloud Logging.
    *   **Priority:** Medium
    *   **Effort:** Small

## Potential Issues / Bug Fixes

1.  **Placeholder CRUD Functions:**
    *   **Category:** Bug / Incomplete Feature
    *   **Description:** The routes currently rely on hypothetical `crud` functions. Without implementation, endpoints like personalized story generation and rating will fail. (Covered by Task #1)
    *   **Priority:** High

2.  **Public GCS URLs for TTS:**
    *   **Category:** Security Risk / Potential Issue
    *   **Description:** `tts_service.py` currently makes uploaded audio files public. This could lead to unauthorized access or high egress costs. Recommend switching to Signed URLs.
    *   **Priority:** Medium

## Potential Enhancements & Optimizations

1.  **Use GCS Signed URLs for TTS Audio:**
    *   **Category:** Security Enhancement
    *   **Description:** Modify `tts_service.py` to generate time-limited Signed URLs for accessing TTS audio files instead of making them public. Requires corresponding changes in the mobile app to request and use these URLs.
    *   **Priority:** Medium
    *   **Effort:** Medium

2.  **Implement Cloud Monitoring Dashboards & Alerts:**
    *   **Category:** Monitoring / Operations Enhancement
    *   **Description:** Set up Google Cloud Monitoring dashboards for key application metrics (latency, errors, resource usage) and configure alerts for critical conditions.
    *   **Priority:** Medium
    *   **Effort:** Medium

3.  **Leverage Advanced Vertex AI Features:**
    *   **Category:** Enhancement / Refactoring
    *   **Description:** Explore using Vertex AI's native `ChatSession` for managing conversation history in `ai_client.py` / `enhanced_ai_client.py`, potentially simplifying the current manual history tracking.
    *   **Priority:** Low
    *   **Effort:** Medium

4.  **Implement API Gateway / IAP:**
    *   **Category:** Security / Infrastructure Enhancement
    *   **Description:** Deploy Google Cloud API Gateway or use Identity-Aware Proxy (IAP) in front of the backend service (Cloud Run/GKE) for enhanced security, rate limiting, authentication management, etc.
    *   **Priority:** Low
    *   **Effort:** Medium to Large

5.  **Refine Personalization Engine:**
    *   **Category:** Enhancement
    *   **Description:** Further refine the `PersonalizationEngine`, potentially adding more sophisticated interest mapping, better handling of conflicting preferences, or integrating more data sources via Google APIs.
    *   **Priority:** Low
    *   **Effort:** Medium to Large

6.  **Mobile App UI/UX Improvements:**
    *   **Category:** UI Improvement (Mobile)
    *   **Description:** Based on user feedback (once available), identify and implement improvements to the mobile app's user interface and experience, particularly around story playback, preference settings, and map interaction.
    *   **Priority:** (Requires User Feedback)
    *   **Effort:** Variable