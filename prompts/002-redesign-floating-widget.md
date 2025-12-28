<objective>
Redesign the floating recording widget from a rectangular text-based design to a modern, circular, icon-only design with smooth animations. The widget should feel like a premium AI voice assistant indicator - minimal, beautiful, and responsive to audio input.
</objective>

<context>
This is the Whisper Voice Input app's main visual indicator. Users see this widget constantly, so it must be:
- Unobtrusive when idle
- Clearly visible when recording
- Aesthetically pleasing and modern
- Responsive to user interaction (drag vs click)

Existing files to modify:
- `./src/ui/widget.py` - Main widget implementation
- `./src/ui/styles.py` - Color constants and styles
- `./src/config/constants.py` - Widget size constants
- `./src/ui/settings.py` - Add widget size option
</context>

<requirements>

<visual_states>

1. **IDLE/READY State**
   - Shape: Perfect circle (default 60px, configurable: 60/80/100px)
   - Background: Dark (#1a1a2e)
   - Border: 2px grey-blue (#6b7b8c)
   - Icon: Microphone outline in grey-blue
   - Animation: Optional very subtle breathing glow (opacity 0.8 → 1.0, 3s cycle)
   - Feel: Calm, waiting, unobtrusive

2. **RECORDING State**
   - Background: Dark (#1a1a2e)
   - Border: 2px bright blue (#00a8ff)
   - Icon: Solid microphone in bright blue (#00a8ff)
   - Animation: Pulsar/ripple waves emanating from center
     - 3 concentric rings expanding outward
     - Rings fade as they expand
     - Ring intensity responds to audio input level
     - Think: AI voice assistant visual (Siri, Google Assistant style)
   - Feel: Active, listening, energetic

3. **PROCESSING State**
   - Background: Dark (#1a1a2e)
   - Border: 2px warm amber (#ffb347)
   - Icon: Microphone with glowing halo effect in amber
   - Animation: Breathing pulse (scale 1.0 → 1.1 → 1.0, 1s cycle)
   - The glow should expand and contract rhythmically
   - Feel: Thinking, working, contemplating

4. **ERROR/NOTHING DETECTED State**
   - Brief flash: Border turns red (#e94560) for 0.5s
   - Then smoothly transitions back to IDLE state
   - Feel: Quick acknowledgment, then reset

</visual_states>

<widget_behavior>

1. **Size Options** (add to settings):
   - Compact: 60px diameter (default)
   - Medium: 80px diameter
   - Large: 100px diameter

2. **Click vs Drag Handling**:
   - Track mouse movement during press
   - Only register as "click" if movement < 5px total
   - If movement >= 5px, treat as drag (no click event)
   - This prevents accidental recording toggles when repositioning

3. **Default Position**:
   - Top-right of screen
   - Below where window control buttons typically appear
   - Approximately: x = screen_width - 100, y = 80

4. **Dragging**:
   - Smooth drag with no snapping
   - Position saved on release
   - Position persists across sessions

</widget_behavior>

<icon_design>
Draw the microphone icon using QPainter (no external icon files needed):
- Simple, recognizable microphone shape
- Proportional to widget size (about 40% of diameter)
- Outline style for idle, filled for recording
- Centered in the circle
</icon_design>

<animation_implementation>
Use QTimer and QPropertyAnimation for smooth animations:

1. **Pulsar Rings** (recording):
   - Create 3 ring objects that expand from center
   - Each ring: starts at icon size, expands to widget edge, fades out
   - Stagger ring starts by ~400ms
   - Ring expansion speed responds to audio level

2. **Breathing Glow** (processing):
   - Animate a blur/glow effect around the icon
   - Use QPainter with radial gradient
   - Pulse opacity and size

3. **State Transitions**:
   - Smooth color transitions between states (200ms)
   - Use QPropertyAnimation for border color changes

</animation_implementation>

</requirements>

<implementation_steps>

1. Update `./src/config/constants.py`:
   - Add WIDGET_SIZES dict with compact/medium/large options
   - Update color constants for new palette

2. Update `./src/ui/styles.py`:
   - Add new color constants (grey-blue, bright-blue, amber)
   - Remove text-related styles

3. Rewrite `./src/ui/widget.py`:
   - Change from QWidget with layout to custom painted circular widget
   - Implement paintEvent for circle, icon, and animations
   - Add PulsarRing class for recording animation
   - Improve click/drag detection logic
   - Add audio level integration for responsive animations

4. Update `./src/ui/settings.py`:
   - Add widget size dropdown (Compact/Medium/Large)
   - Wire up to settings

5. Update `./src/app.py`:
   - Pass audio levels to widget for animation response
   - Handle new widget size setting

</implementation_steps>

<constraints>
- No external icon libraries - draw everything with QPainter
- Keep the widget lightweight - animations should not impact CPU
- Maintain existing functionality (click to toggle, tray integration)
- Colors must work well on both light and dark backgrounds
- All animations should be smooth 60fps where possible
</constraints>

<output>
Modify these files:
- `./src/config/constants.py` - Add size constants and new colors
- `./src/ui/styles.py` - Update color palette
- `./src/ui/widget.py` - Complete rewrite for circular design
- `./src/ui/settings.py` - Add widget size option
- `./src/app.py` - Minor updates for new widget API
</output>

<verification>
After implementation, verify:
1. Widget appears as a circle in top-right corner
2. Microphone icon is clearly visible and centered
3. Click toggles recording (drag does not)
4. Recording state shows pulsing rings
5. Rings respond to audio input level
6. Processing state shows breathing glow
7. Error state briefly flashes red then returns to idle
8. Widget size can be changed in settings
9. All animations are smooth (no stuttering)
10. Position saves correctly after dragging
</verification>

<success_criteria>
- Widget looks like a modern AI voice assistant indicator
- No text visible anywhere on the widget
- Clear visual distinction between all four states
- Smooth, polished animations
- Reliable click vs drag detection
- Settings integration for size preference
</success_criteria>
