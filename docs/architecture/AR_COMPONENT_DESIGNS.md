# AR Component Design Specifications

## 1. Core AR Components

### 1.1 ARSafetyOverlay Component
**Purpose**: Manages safety-critical AR display rules

```typescript
interface ARSafetyOverlayProps {
  vehicleSpeed: number;
  isDriverSide: boolean;
  weatherCondition: 'clear' | 'rain' | 'fog' | 'snow';
  timeOfDay: 'day' | 'night' | 'twilight';
  passengerAge: 'adult' | 'child';
}

// Visual specs:
- Opacity: 0% when vehicleSpeed > 70mph
- Fade transition: 2 seconds
- Emergency hide: Instant (0ms)
- Max viewport coverage: 30%
```

### 1.2 ARPointOfInterest Component
**Purpose**: Display contextual information about locations

```
Design Mockup:
╭─────────────────────────╮
│ 🏛️ Lincoln Memorial     │ ← Icon + Title
│ ━━━━━━━━━━━━━━━━━━━━━ │ ← Progress indicator
│ 📍 0.8 mi • 2 min       │ ← Distance + ETA
│                         │
│ "Tap to hear the story" │ ← CTA with voice icon
╰─────────────────────────╯

Interaction states:
- Default: Semi-transparent (80% opacity)
- Hover: Full opacity + gentle glow
- Active: Pulse animation + haptic
- Dismissed: Slide out + fade
```

### 1.3 ARStoryPath Component
**Purpose**: Visualize narrative journey progression

```
Visual Design:
    ┌─┐     ┌─┐     ┌─┐     ┌─┐
    │1│────▶│2│────▶│3│────▶│4│
    └─┘     └─┘     └─┘     └─┘
  Visited  Current   Next   Future

Node States:
- Visited: Filled circle, 60% opacity
- Current: Pulsing glow, 100% opacity
- Upcoming: Outlined circle, 40% opacity
- Locked: Grayed out with lock icon
```

### 1.4 ARHistoricalLens Component
**Purpose**: Time-travel overlay showing historical views

```
Layer Structure:
┌─────────────────────────────┐
│ Camera Feed (Base Layer)    │
├─────────────────────────────┤
│ Historical Image (Blend)    │ ← 50% opacity
│ • Sepia tone filter         │
│ • Soft vignette edges       │
├─────────────────────────────┤
│ Info Card (Top Layer)       │
│ "San Francisco, 1906"       │
│ [Slider: Then ←→ Now]       │
└─────────────────────────────┘
```

## 2. Specialized AR Experiences

### 2.1 Wildlife Spotter AR
```typescript
interface WildlifeSpotterProps {
  species: string;
  rarity: 'common' | 'uncommon' | 'rare';
  distance: number;
  behaviorHints: string[];
}
```

**Visual Design**:
```
    🦌 White-tailed Deer
   ╱ ╲  Spotted at 2:30 PM
  ╱   ╲ 
 │ 👁️ │ "Look carefully near the treeline"
 │    │ 
  ╲  ╱  Rarity: ⭐⭐⭐ (Uncommon)
   ╲╱   
```

### 2.2 Landmark Comparison AR
**Before/After Historical Views**

```
┌─────────────┬─────────────┐
│    Then     │     Now     │
│   (1920)    │   (2024)    │
├─────────────┼─────────────┤
│             │             │
│  [Old IMG]  │ [Live Feed] │
│             │             │
├─────────────┴─────────────┤
│ Swipe to blend views ←→   │
└───────────────────────────┘
```

### 2.3 Interactive Story Choice AR
```
     "The Mystery at Miner's Creek"
              Choose your path:
                    
         💎                      👻
    Search the           Visit the old
      mines              ghost town
                    
    [15 min detour]    [8 min detour]
```

## 3. AR Animation Specifications

### 3.1 Entrance Animations

#### Fade Scale In
```
Timeline (300ms):
0ms    ➤ opacity: 0, scale: 0.8
100ms  ➤ opacity: 0.5, scale: 0.9
300ms  ➤ opacity: 1.0, scale: 1.0
Easing: cubic-bezier(0.34, 1.56, 0.64, 1)
```

#### Slide Up Reveal
```
Timeline (400ms):
0ms    ➤ translateY: 50px, opacity: 0
200ms  ➤ translateY: 10px, opacity: 0.7
400ms  ➤ translateY: 0px, opacity: 1.0
Easing: cubic-bezier(0.25, 0.46, 0.45, 0.94)
```

### 3.2 Idle Animations

#### Gentle Float
```
Keyframes (4000ms loop):
0%    ➤ translateY: 0px
50%   ➤ translateY: -10px
100%  ➤ translateY: 0px
Easing: ease-in-out
```

#### Attention Pulse
```
Keyframes (2000ms loop):
0%    ➤ scale: 1.0, glow: 0
50%   ➤ scale: 1.05, glow: 20px
100%  ➤ scale: 1.0, glow: 0
```

### 3.3 Interaction Feedback

#### Tap Response
```
Timeline (200ms):
0ms    ➤ scale: 1.0
50ms   ➤ scale: 0.95
100ms  ➤ scale: 1.1
200ms  ➤ scale: 1.0
+ Haptic: Impact.light()
```

## 4. AR Audio Integration

### 4.1 Spatial Audio Cues
```typescript
interface ARSpatialAudio {
  source: ARElement;
  volume: number; // 0-1 based on distance
  pan: number;    // -1 (left) to 1 (right)
  reverb: number; // Environmental echo
}

// Distance-based volume curve
0-10m:   100% volume
10-50m:  Linear falloff to 50%
50-100m: Linear falloff to 20%
>100m:   10% (ambient only)
```

### 4.2 Audio Notification Patterns
```
Discovery Chime:
♪ C5 (100ms) → E5 (100ms) → G5 (200ms)

Selection Confirm:
♪ G4 (50ms) → G5 (100ms)

Navigation Alert:
♪ E5 (200ms) → E5 (200ms) [pause] → E5 (400ms)
```

## 5. Gesture Recognition Specs

### 5.1 Touch Gesture Library

#### AR Tap
- Recognition: Touch down + up within 150ms
- Movement tolerance: 10px
- Target expansion: +20px invisible padding

#### AR Swipe
- Recognition: Touch move > 50px in 300ms
- Direction detection: 8-way (N,NE,E,SE,S,SW,W,NW)
- Velocity threshold: 200px/second

#### AR Long Press
- Recognition: Touch hold for 1000ms
- Visual feedback: Radial progress indicator
- Haptic: Continuous gentle pulse

### 5.2 Advanced Gestures

#### Pinch to Focus
```
Two-finger detection:
- Initial distance: D1
- Current distance: D2
- Scale factor: D2/D1
- Min scale: 0.5x
- Max scale: 3.0x
```

#### Draw to Select
```
Path recognition:
- Minimum points: 10
- Closure detection: Start/end within 30px
- Shape analysis: Circle/rectangle detection
- Selection: Elements with >70% overlap
```

## 6. Adaptive AR System

### 6.1 Context-Aware Adjustments

```typescript
interface ARContextAdapter {
  // Speed-based simplification
  speedThresholds: {
    full: 0-30,     // mph - All AR features
    reduced: 31-50, // Simplified AR
    minimal: 51-70, // Critical info only
    hidden: 71+     // No AR
  };
  
  // Time-based adjustments
  nightMode: {
    brightness: 0.6,      // 60% of day brightness
    contrastBoost: 1.3,   // 30% higher contrast
    colorTemp: 'warm'     // 3000K vs 6500K
  };
  
  // Weather adaptations
  weatherModes: {
    rain: { contrast: 1.5, glowIntensity: 2.0 },
    fog:  { contrast: 2.0, glowIntensity: 3.0 },
    snow: { contrast: 1.8, colorTemp: 'cool' }
  };
}
```

### 6.2 Performance Scaling

```typescript
interface ARPerformanceScaler {
  qualityLevels: {
    ultra: {
      maxElements: 20,
      updateRate: 60,    // fps
      particleCount: 1000,
      shadowQuality: 'high'
    },
    high: {
      maxElements: 15,
      updateRate: 30,
      particleCount: 500,
      shadowQuality: 'medium'
    },
    balanced: {
      maxElements: 10,
      updateRate: 30,
      particleCount: 200,
      shadowQuality: 'low'
    },
    battery: {
      maxElements: 5,
      updateRate: 15,
      particleCount: 0,
      shadowQuality: 'none'
    }
  };
}
```

## 7. AR Accessibility Components

### 7.1 Visual Accessibility Overlays

```
High Contrast Mode:
┌─────────────────────────┐
│ ████ Historical Site    │ ← Black bg, white text
│ ████████████████████    │ ← High contrast icons
│ Distance: 2.3 miles     │ ← Increased font size
└─────────────────────────┘

Color Blind Friendly Palette:
- Information: Blue #0066CC → Safe for all types
- Success: Teal #17A2B8 → Distinguishable
- Warning: Orange #FD7E14 → High visibility
- Danger: Magenta #E83E8C → Clear contrast
```

### 7.2 Motor Accessibility Features

```typescript
interface ARAccessibilityControls {
  dwellSelection: {
    enabled: boolean;
    dwellTime: 1500; // ms
    visualIndicator: 'radial' | 'border';
  };
  
  voiceControl: {
    commands: [
      "select [element name]",
      "dismiss all",
      "show more",
      "navigate to"
    ];
  };
  
  simplifiedGestures: {
    tapAnywhere: 'select nearest',
    swipeAnywhere: 'dismiss all',
    shakeDevice: 'reset view'
  };
}
```

## 8. AR Debug Overlay

For development and testing:

```
┌─────────────────────────────────┐
│ AR Debug Info                   │
│ FPS: 58.2 | Elements: 7         │
│ CPU: 23% | GPU: 45% | RAM: 128MB│
│ Tracking: Good | GPS: ±5m       │
│ ─────────────────────────────── │
│ Vehicle Speed: 45 mph           │
│ Heading: 276° | Pitch: -2°      │
│ Weather: Clear | Time: Day      │
│ Battery: 72% | Temp: Normal     │
└─────────────────────────────────┘
```

## 9. AR Content Templates

### 9.1 Story Point Template
```xml
<ARStoryPoint>
  <Header>
    <Icon>landmark</Icon>
    <Title>The Great Train Robbery</Title>
    <Year>1873</Year>
  </Header>
  <Content>
    <Distance>1.2 miles</Distance>
    <Duration>3 min story</Duration>
    <Teaser>Where Jesse James made history...</Teaser>
  </Content>
  <Actions>
    <Primary>Play Story</Primary>
    <Secondary>Save for Later</Secondary>
  </Actions>
</ARStoryPoint>
```

### 9.2 Navigation Hint Template
```xml
<ARNavigationHint>
  <Direction>slight-right</Direction>
  <Distance>500ft</Distance>
  <Landmark>After the red barn</Landmark>
  <VisualCue>
    <Arrow angle="30" />
    <Glow color="#00FF00" />
  </VisualCue>
</ARNavigationHint>
```

## 10. AR Testing Protocols

### 10.1 Motion Testing Scenarios
1. Smooth highway driving (constant speed)
2. Winding mountain roads (variable pitch/roll)
3. Stop-and-go traffic (acceleration changes)
4. Passenger head movement simulation
5. Vehicle vibration conditions

### 10.2 Environmental Testing
1. Bright sunlight (10,000+ lux)
2. Night driving (< 10 lux)
3. Tunnel transitions (rapid light change)
4. Rain/snow visual obstruction
5. Foggy conditions (low contrast)

### 10.3 Performance Benchmarks
- AR element render time: < 16ms (60fps)
- Touch response latency: < 100ms
- Voice command recognition: < 500ms
- Memory usage: < 150MB
- Battery impact: < 10% per hour