"""Circular floating recording widget with audio-reactive visualizations."""

import math
import random
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient,
    QPainterPath, QPaintEvent, QMouseEvent, QEnterEvent, QFont,
    QLinearGradient
)

from ..config.constants import (
    WIDGET_SIZES,
    DEFAULT_WIDGET_SIZE,
    WIDGET_OPACITY,
    STATE_IDLE,
    STATE_RECORDING,
    STATE_PROCESSING,
    STATE_ERROR,
)
from .styles import (
    COLOR_BG_DARK,
    COLOR_WIDGET_IDLE,
    COLOR_WIDGET_RECORDING,
    COLOR_WIDGET_PROCESSING,
    COLOR_WIDGET_ERROR,
)


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value between min and max to prevent floating point errors."""
    return max(min_val, min(max_val, value))


# Thickness scale factors by widget size
THICKNESS_SCALE = {
    "compact": 0.6,
    "medium": 0.8,
    "large": 1.0,
}


class FrequencyBar:
    """A single frequency bar that animates with audio."""

    def __init__(self, angle: float, base_height: float):
        self.angle = angle
        self.base_height = base_height
        self.current_height = 0.0
        self.target_height = 0.0
        self.velocity = 0.0
        # Each bar has slightly different response characteristics
        self.sensitivity = random.uniform(0.7, 1.3)
        self.decay = random.uniform(0.85, 0.92)

    def update(self, audio_level: float):
        """Update bar height with spring-like physics."""
        # Set new target based on audio (with some randomness for organic feel)
        noise = random.uniform(-0.15, 0.15)
        self.target_height = self.base_height * (0.3 + audio_level * self.sensitivity + noise)
        self.target_height = clamp(self.target_height, 0, self.base_height)

        # Spring physics for smooth animation
        spring = 0.3
        damping = 0.7

        force = (self.target_height - self.current_height) * spring
        self.velocity = (self.velocity + force) * damping
        self.current_height += self.velocity
        self.current_height = clamp(self.current_height, 0, self.base_height)


class PulseRing:
    """A simple expanding pulse ring."""

    def __init__(self):
        self.progress = 0.0
        self.active = False

    def reset(self):
        self.progress = 0.0
        self.active = True

    def update(self, speed: float = 0.03):
        if self.active:
            self.progress += speed
            if self.progress >= 1.0:
                self.active = False
                self.progress = 0.0

    @property
    def opacity(self) -> float:
        # Fade out as it expands
        return clamp(1.0 - self.progress ** 0.5)


class InfoTooltip(QWidget):
    """Custom styled tooltip for the widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.ToolTip
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the tooltip UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self._title = QLabel("Voice Input")
        self._title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self._title.setStyleSheet(f"color: {COLOR_WIDGET_RECORDING}; background: transparent;")
        layout.addWidget(self._title)

        self._action = QLabel("Click to Transcribe")
        self._action.setFont(QFont("Segoe UI", 9))
        self._action.setStyleSheet(f"color: #cccccc; background: transparent;")
        layout.addWidget(self._action)

        self.adjustSize()

    def set_text(self, title: str, action: str) -> None:
        """Update tooltip text."""
        self._title.setText(title)
        self._action.setText(action)
        self.adjustSize()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw tooltip background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor(COLOR_BG_DARK)
        bg_color.setAlpha(240)
        painter.setBrush(bg_color)

        border_color = QColor(COLOR_WIDGET_RECORDING)
        border_color.setAlpha(150)
        painter.setPen(QPen(border_color, 1))

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect, 6, 6)

    def show_at(self, widget_center: QPoint, widget_size: int):
        """Show tooltip centered below widget, respecting screen boundaries."""
        self.adjustSize()
        tooltip_width = self.width()
        tooltip_height = self.height()

        # Position: centered horizontally, top starts halfway between widget center and bottom
        tooltip_x = widget_center.x() - tooltip_width // 2
        tooltip_y = widget_center.y() + widget_size // 4

        # Get screen boundaries
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            padding = 5

            # Adjust horizontal position if outside screen
            if tooltip_x < geometry.x() + padding:
                tooltip_x = geometry.x() + padding
            elif tooltip_x + tooltip_width > geometry.x() + geometry.width() - padding:
                tooltip_x = geometry.x() + geometry.width() - tooltip_width - padding

            # Adjust vertical position if outside screen
            if tooltip_y + tooltip_height > geometry.y() + geometry.height() - padding:
                tooltip_y = geometry.y() + geometry.height() - tooltip_height - padding
            if tooltip_y < geometry.y() + padding:
                tooltip_y = geometry.y() + padding

        self.move(tooltip_x, tooltip_y)
        self.show()


class FloatingWidget(QWidget):
    """Circular floating widget with stunning audio-reactive visualizations."""

    clicked = pyqtSignal()

    def __init__(self, size_key: str = DEFAULT_WIDGET_SIZE, parent=None):
        super().__init__(parent)
        self._size_key = size_key
        self._size = WIDGET_SIZES.get(size_key, WIDGET_SIZES["compact"])
        self._thickness_scale = THICKNESS_SCALE.get(size_key, 1.0)
        self._state = STATE_IDLE
        self._audio_level = 0.0
        self._smoothed_audio = 0.0  # Smoothed for glow effect

        # Drag handling
        self._drag_start_pos: QPoint | None = None
        self._drag_start_widget_pos: QPoint | None = None
        self._total_drag_distance = 0

        # Animation state
        self._frequency_bars: list[FrequencyBar] = []
        self._pulse_rings: list[PulseRing] = []
        self._glow_intensity = 0.0
        self._breathing_scale = 1.0
        self._breathing_direction = 1
        self._idle_glow = 0.6
        self._idle_glow_direction = 1
        self._idle_border_width = 2.5
        self._error_flash_alpha = 0
        self._rotation_offset = 0.0  # Slow rotation for visual interest

        # Tooltip
        self._tooltip = InfoTooltip()
        self._tooltip.hide()

        # Timers
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animations)
        self._animation_timer.start(16)  # ~60fps

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._spawn_pulse)

        self._error_timer = QTimer(self)
        self._error_timer.timeout.connect(self._clear_error)
        self._error_timer.setSingleShot(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Initialize the widget."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFixedSize(self._size, self._size)
        self.setWindowOpacity(WIDGET_OPACITY)

        self._init_visualizers()
        self._position_top_right()

    def _init_visualizers(self) -> None:
        """Initialize frequency bars and pulse rings."""
        # Create frequency bars around the circle (24 bars for smooth look)
        num_bars = 24
        bar_height = self._size * 0.15  # Max bar height
        self._frequency_bars = []
        for i in range(num_bars):
            angle = (2 * math.pi * i) / num_bars
            self._frequency_bars.append(FrequencyBar(angle, bar_height))

        # Create pulse rings (3 rings with staggered timing)
        self._pulse_rings = [PulseRing() for _ in range(3)]

    def _position_top_right(self) -> None:
        """Position widget in top-right corner."""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.width() - self._size - 20
            y = 80
            self.move(x, y)

    def _ensure_on_screen(self) -> None:
        """Ensure widget stays within screen boundaries."""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            pos = self.pos()
            new_x = pos.x()
            new_y = pos.y()

            if new_x + self._size > geometry.width():
                new_x = geometry.width() - self._size - 10
            if new_y + self._size > geometry.height():
                new_y = geometry.height() - self._size - 10
            if new_x < 0:
                new_x = 10
            if new_y < 0:
                new_y = 10

            if new_x != pos.x() or new_y != pos.y():
                self.move(new_x, new_y)

    def set_size(self, size_key: str) -> None:
        """Change widget size."""
        if size_key in WIDGET_SIZES:
            self._size_key = size_key
            self._size = WIDGET_SIZES[size_key]
            self._thickness_scale = THICKNESS_SCALE.get(size_key, 1.0)
            self.setFixedSize(self._size, self._size)
            self._init_visualizers()
            self._ensure_on_screen()
            self.update()

    def _get_scaled_thickness(self, base_thickness: float) -> float:
        """Get thickness scaled by widget size."""
        return base_thickness * self._thickness_scale

    def _get_state_color(self) -> QColor:
        """Get color for current state."""
        colors = {
            STATE_IDLE: COLOR_WIDGET_IDLE,
            STATE_RECORDING: COLOR_WIDGET_RECORDING,
            STATE_PROCESSING: COLOR_WIDGET_PROCESSING,
            STATE_ERROR: COLOR_WIDGET_ERROR,
        }
        return QColor(colors.get(self._state, COLOR_WIDGET_IDLE))

    def _spawn_pulse(self) -> None:
        """Spawn a new pulse ring."""
        for ring in self._pulse_rings:
            if not ring.active:
                ring.reset()
                break

    def _update_animations(self) -> None:
        """Update all animations."""
        needs_update = False

        # Smooth audio level for glow effect
        self._smoothed_audio += (self._audio_level - self._smoothed_audio) * 0.15

        if self._state == STATE_RECORDING:
            # Update frequency bars
            for bar in self._frequency_bars:
                bar.update(self._audio_level)

            # Update pulse rings
            for ring in self._pulse_rings:
                if ring.active:
                    ring.update(0.025 + self._audio_level * 0.02)

            # Update glow intensity
            self._glow_intensity = 0.5 + self._smoothed_audio * 0.5

            # Slow rotation for visual interest
            self._rotation_offset += 0.005
            if self._rotation_offset > 2 * math.pi:
                self._rotation_offset -= 2 * math.pi

            needs_update = True

        # Update breathing animation (processing)
        if self._state == STATE_PROCESSING:
            self._breathing_scale += self._breathing_direction * 0.008
            if self._breathing_scale >= 1.25:
                self._breathing_direction = -1
            elif self._breathing_scale <= 1.0:
                self._breathing_direction = 1
            needs_update = True

        # Update idle glow
        if self._state == STATE_IDLE:
            self._idle_glow += self._idle_glow_direction * 0.008
            if self._idle_glow >= 1.0:
                self._idle_glow_direction = -1
            elif self._idle_glow <= 0.4:
                self._idle_glow_direction = 1

            self._idle_border_width += self._idle_glow_direction * 0.02
            self._idle_border_width = clamp(self._idle_border_width, 2.0, 3.5)
            needs_update = True

        # Update error flash
        if self._error_flash_alpha > 0:
            self._error_flash_alpha = max(0, self._error_flash_alpha - 10)
            needs_update = True

        if needs_update:
            self.update()

    def _clear_error(self) -> None:
        """Clear error state."""
        self._state = STATE_IDLE
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the circular widget with visualizations."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = QPointF(self._size / 2, self._size / 2)
        radius = (self._size / 2) - 4

        # Recording visualizations (behind everything)
        if self._state == STATE_RECORDING:
            self._draw_outer_glow(painter, center, radius)
            self._draw_pulse_rings(painter, center, radius)
            self._draw_frequency_bars(painter, center, radius)

        # Draw main circle background
        self._draw_background(painter, center, radius)

        # Draw border
        self._draw_border(painter, center, radius)

        # Draw condenser microphone icon
        self._draw_condenser_mic(painter, center)

        # Draw processing glow
        if self._state == STATE_PROCESSING:
            self._draw_processing_glow(painter, center, radius)

        # Draw idle glow effect
        if self._state == STATE_IDLE:
            self._draw_idle_glow(painter, center, radius)

        # Draw error flash overlay
        if self._error_flash_alpha > 0:
            self._draw_error_flash(painter, center, radius)

    def _draw_outer_glow(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw intense outer glow during recording."""
        color = QColor(COLOR_WIDGET_RECORDING)

        # Multiple glow layers for richness
        for i in range(3):
            glow_radius = radius + 8 + i * 6
            alpha = clamp(self._glow_intensity * (0.4 - i * 0.1))

            gradient = QRadialGradient(center, glow_radius)
            color.setAlphaF(0.0)
            gradient.setColorAt(0.6, color)
            color.setAlphaF(alpha)
            gradient.setColorAt(1.0, color)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(center, glow_radius, glow_radius)

    def _draw_pulse_rings(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw expanding pulse rings."""
        color = QColor(COLOR_WIDGET_RECORDING)
        base_thickness = self._get_scaled_thickness(2.0)

        for ring in self._pulse_rings:
            if ring.active:
                ring_radius = radius + ring.progress * self._size * 0.3
                alpha = clamp(ring.opacity * 0.6)
                color.setAlphaF(alpha)

                pen = QPen(color, base_thickness * (1 - ring.progress * 0.5))
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, ring_radius, ring_radius)

    def _draw_frequency_bars(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw audio-reactive frequency bars around the circle."""
        color = QColor(COLOR_WIDGET_RECORDING)
        bar_width = self._get_scaled_thickness(3.5)

        # Bar starts just outside the main circle
        bar_start_radius = radius + 3

        for bar in self._frequency_bars:
            if bar.current_height < 1:
                continue

            angle = bar.angle + self._rotation_offset

            # Calculate bar endpoints
            start_x = center.x() + bar_start_radius * math.cos(angle)
            start_y = center.y() + bar_start_radius * math.sin(angle)
            end_x = center.x() + (bar_start_radius + bar.current_height) * math.cos(angle)
            end_y = center.y() + (bar_start_radius + bar.current_height) * math.sin(angle)

            # Color intensity based on height
            intensity = bar.current_height / bar.base_height
            color.setAlphaF(clamp(0.5 + intensity * 0.5))

            pen = QPen(color, bar_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))

    def _draw_background(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw the dark circular background."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLOR_BG_DARK))
        painter.drawEllipse(center, radius, radius)

    def _draw_border(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw the colored border."""
        color = self._get_state_color()

        base_width = 2.5
        if self._state == STATE_IDLE:
            base_width = self._idle_border_width
            color.setAlphaF(clamp(self._idle_glow))
        elif self._state == STATE_RECORDING:
            # Thicker, brighter border during recording
            base_width = 3.0 + self._smoothed_audio * 1.5
            color.setAlphaF(clamp(0.8 + self._smoothed_audio * 0.2))

        border_width = self._get_scaled_thickness(base_width)
        pen = QPen(color, border_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

    def _draw_idle_glow(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw subtle glow during idle state."""
        color = QColor(COLOR_WIDGET_IDLE)
        glow_radius = radius + 3

        gradient = QRadialGradient(center, glow_radius)
        color.setAlphaF(0.0)
        gradient.setColorAt(0.7, color)
        color.setAlphaF(clamp(self._idle_glow * 0.2))
        gradient.setColorAt(1.0, color)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, glow_radius, glow_radius)

    def _draw_condenser_mic(self, painter: QPainter, center: QPointF) -> None:
        """Draw condenser microphone icon."""
        color = self._get_state_color()
        icon_size = self._size * 0.5

        if self._state == STATE_PROCESSING:
            icon_size *= self._breathing_scale

        line_thick = self._get_scaled_thickness(2.0)
        line_thin = self._get_scaled_thickness(1.5)

        head_width = icon_size * 0.5
        head_height = icon_size * 0.55
        head_x = center.x() - head_width / 2
        head_y = center.y() - icon_size * 0.35

        if self._state in (STATE_RECORDING, STATE_PROCESSING):
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(color, line_thin))

        head_rect = QRectF(head_x, head_y, head_width, head_height)
        painter.drawRoundedRect(head_rect, head_width / 2, head_width / 2)

        if self._state in (STATE_RECORDING, STATE_PROCESSING):
            slot_color = QColor(COLOR_BG_DARK)
            painter.setBrush(slot_color)
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            painter.setPen(QPen(color, line_thin))

        slot_width = head_width * 0.6
        slot_height = max(1.5, icon_size * 0.03)
        slot_x = center.x() - slot_width / 2
        slot_spacing = head_height * 0.2

        for i in range(3):
            slot_y = head_y + head_height * 0.25 + i * slot_spacing
            if self._state in (STATE_RECORDING, STATE_PROCESSING):
                painter.drawRoundedRect(
                    QRectF(slot_x, slot_y, slot_width, slot_height),
                    slot_height / 2, slot_height / 2
                )
            else:
                painter.drawLine(
                    QPointF(slot_x, slot_y + slot_height / 2),
                    QPointF(slot_x + slot_width, slot_y + slot_height / 2)
                )

        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._state in (STATE_RECORDING, STATE_PROCESSING):
            painter.setPen(QPen(color, line_thick))
        else:
            painter.setPen(QPen(color, line_thin))

        cradle_rect = QRectF(
            head_x - head_width * 0.15,
            head_y + head_height * 0.4,
            head_width * 1.3,
            head_height * 0.8
        )
        painter.drawArc(cradle_rect, 0, 180 * 16)

        stand_x = center.x()
        stand_top = head_y + head_height + head_height * 0.25
        stand_height = icon_size * 0.15

        if self._state in (STATE_RECORDING, STATE_PROCESSING):
            painter.setPen(QPen(color, line_thick))
        painter.drawLine(
            QPointF(stand_x, stand_top),
            QPointF(stand_x, stand_top + stand_height)
        )

        base_width = icon_size * 0.35
        base_y = stand_top + stand_height
        painter.drawLine(
            QPointF(center.x() - base_width / 2, base_y),
            QPointF(center.x() + base_width / 2, base_y)
        )

    def _draw_processing_glow(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw breathing glow during processing."""
        color = QColor(COLOR_WIDGET_PROCESSING)

        glow_radius = radius * self._breathing_scale + 5
        gradient = QRadialGradient(center, glow_radius)
        color.setAlphaF(0.0)
        gradient.setColorAt(0.5, color)
        alpha = clamp((self._breathing_scale - 1.0) * 2.5)
        color.setAlphaF(alpha)
        gradient.setColorAt(1.0, color)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, glow_radius, glow_radius)

    def _draw_error_flash(self, painter: QPainter, center: QPointF, radius: float) -> None:
        """Draw red flash overlay for error state."""
        color = QColor(COLOR_WIDGET_ERROR)
        color.setAlpha(self._error_flash_alpha)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(center, radius, radius)

    def set_state(self, state: str, message: str = "") -> None:
        """Update widget state."""
        self._state = state

        if state == STATE_RECORDING:
            if not self._pulse_timer.isActive():
                self._pulse_timer.start(400)
            # Reset bars
            for bar in self._frequency_bars:
                bar.current_height = 0
                bar.velocity = 0
        else:
            self._pulse_timer.stop()
            for ring in self._pulse_rings:
                ring.active = False

        if state == STATE_ERROR:
            self._error_flash_alpha = 180
            self._error_timer.start(800)

        if state == STATE_PROCESSING:
            self._breathing_scale = 1.0
            self._breathing_direction = 1

        self.update()

    def set_audio_level(self, level: float) -> None:
        """Update audio level for reactive animations."""
        self._audio_level = clamp(level)

    def enterEvent(self, event: QEnterEvent) -> None:
        """Show tooltip on hover."""
        if self._state == STATE_IDLE:
            self._tooltip.set_text("Voice Input", "Click to Record")
            widget_center = self.mapToGlobal(QPoint(self._size // 2, self._size // 2))
            self._tooltip.show_at(widget_center, self._size)
        elif self._state == STATE_RECORDING:
            self._tooltip.set_text("Recording", "Click to Transcribe")
            widget_center = self.mapToGlobal(QPoint(self._size // 2, self._size // 2))
            self._tooltip.show_at(widget_center, self._size)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Hide tooltip."""
        self._tooltip.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        self._tooltip.hide()
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_start_widget_pos = self.pos()
            self._total_drag_distance = 0
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle drag."""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_start_pos:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            self._total_drag_distance = abs(delta.x()) + abs(delta.y())

            if self._drag_start_widget_pos:
                new_pos = self._drag_start_widget_pos + delta
                self.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self._total_drag_distance < 5:
                self.clicked.emit()

            self._drag_start_pos = None
            self._drag_start_widget_pos = None
            self._total_drag_distance = 0
            event.accept()

    def save_position(self) -> tuple[int, int]:
        """Get current position for saving."""
        pos = self.pos()
        return (pos.x(), pos.y())

    def restore_position(self, position: tuple[int, int] | None) -> None:
        """Restore saved position."""
        if position:
            self.move(position[0], position[1])
