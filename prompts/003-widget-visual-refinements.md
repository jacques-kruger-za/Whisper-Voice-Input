<objective>
Refine the floating widget visuals based on user feedback: new condenser microphone icon, dark teal background, smaller sizes, screen boundary handling, settings styling, tray icon sync, bug fixes, and more prominent animations.
</objective>

<context>
The voice input widget is working but needs visual polish. The user wants:
- A professional condenser microphone icon (rounded head with horizontal sound slots)
- Consistent teal blue color theme
- More visible state animations
- System tray that matches widget state

Files to modify:
- `./src/ui/widget.py` - Icon drawing, animations, screen boundary
- `./src/ui/tray.py` - State color sync
- `./src/ui/styles.py` - Settings window colors
- `./src/config/constants.py` - Widget sizes
</context>

<requirements>

<icon_redesign>
Replace current simple microphone with a **condenser microphone** icon:
- Rounded/oval head (not rectangular)
- 3-4 horizontal slots/lines across the head (sound pickup pattern)
- Curved cradle/mount around the lower portion of the head
- Vertical stand below
- Flat base at bottom

The icon should be recognizable at all sizes (40px to 100px).
Draw using QPainter - no external images needed.
</icon_redesign>

<color_changes>
1. **Widget background**: Change from `#1a1a2e` (dark grey) to a dark teal blue that complements the bright blue (`#00a8ff`). Suggested: `#0a1628` or `#0d2137`

2. **Settings window**: Change all red/highlight text (`#e94560`) to the bright blue (`#00a8ff`) for consistency
</color_changes>

<size_adjustments>
Update WIDGET_SIZES in constants.py:
- compact: 40px (was 60px) - smaller, more unobtrusive
- medium: 60px (was 80px)
- large: 80px (was 100px)
</size_adjustments>

<screen_boundary>
When widget size changes (via settings), check if the new size would place the widget outside screen boundaries. If so, move the widget inward to keep it fully visible.

Implementation in `set_size()` method:
1. After resizing, get screen geometry
2. Check if widget right edge > screen right
3. Check if widget bottom edge > screen bottom
4. Adjust position to keep widget on-screen
</screen_boundary>

<tray_icon_sync>
Update `./src/ui/tray.py` to:
1. Create icons that match widget state colors:
   - IDLE: Grey-blue (`#6b7b8c`)
   - RECORDING: Bright blue (`#00a8ff`)
   - PROCESSING: Amber (`#ffb347`)
2. Update icon immediately when state changes (no delay)
3. Use the same condenser mic icon shape for consistency
</tray_icon_sync>

<bug_fix>
Fix the `QColor::setAlphaF: invalid value -1.9984e-16` error.

This is a floating point precision issue. In `widget.py`, add clamping to all `setAlphaF()` calls:
```python
color.setAlphaF(max(0.0, min(1.0, alpha_value)))
```

Apply to:
- `_draw_border()` - idle glow alpha
- `_draw_pulsar_rings()` - ring opacity
- `_draw_processing_glow()` - glow alpha
- Any other places using setAlphaF
</bug_fix>

<animation_improvements>
Make all state visualizations more prominent and visible:

1. **IDLE breathing**:
   - Increase opacity range from 0.7-1.0 to 0.5-1.0
   - Add subtle border width pulsing (2px to 3px)
   - Consider a very faint glow effect

2. **RECORDING pulsar rings**:
   - Increase ring thickness from 2px to 3px
   - Make rings start larger (closer to icon edge)
   - Increase ring opacity from 0.6 to 0.8
   - Add more rings (4-5 instead of 3)
   - Faster spawn rate (300ms instead of 400ms)
   - Add inner glow to the widget during recording

3. **PROCESSING breathing**:
   - Increase scale range from 1.0-1.15 to 1.0-1.25
   - Make glow more visible (higher alpha)
   - Consider amber color bleeding into border
</animation_improvements>

</requirements>

<implementation_steps>

1. **Update constants.py**:
   - Change WIDGET_SIZES values (40, 60, 80)
   - Update COLOR_BACKGROUND to dark teal

2. **Update styles.py**:
   - Change COLOR_HIGHLIGHT from red to bright blue
   - Update any references in SETTINGS_STYLE

3. **Update widget.py**:
   - Rewrite `_draw_microphone()` for condenser mic shape
   - Add alpha clamping to all setAlphaF calls
   - Implement screen boundary check in `set_size()`
   - Enhance idle breathing animation
   - Enhance recording pulsar animation (more rings, thicker, brighter)
   - Enhance processing glow animation

4. **Update tray.py**:
   - Update `_create_icon()` to draw condenser mic shape
   - Ensure icons use correct state colors
   - Verify state updates are responsive

</implementation_steps>

<output>
Modify these files:
- `./src/config/constants.py`
- `./src/ui/styles.py`
- `./src/ui/widget.py`
- `./src/ui/tray.py`
</output>

<verification>
After implementation, verify:
1. Widget shows condenser mic icon (rounded head, horizontal slots)
2. Background is dark teal blue
3. Compact widget is noticeably smaller (40px)
4. Changing widget size keeps it on-screen
5. Settings window uses blue instead of red for highlights
6. Tray icon changes color to match widget state
7. No QColor::setAlphaF errors in console
8. Idle state has visible breathing animation
9. Recording state has prominent pulsar rings
10. Processing state has strong breathing glow
</verification>

<success_criteria>
- Condenser mic icon is recognizable at all sizes
- Color theme is consistently teal blue
- All animations are clearly visible
- Tray icon matches widget state
- No console errors
- Widget stays on-screen after resize
</success_criteria>
