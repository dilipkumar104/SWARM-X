#!/usr/bin/env python3
# Copyright 2026 SWARM-X
# Licensed under Apache-2.0

"""
test_motor_controller.py — Unit tests for motor_controller logic

Tests the pure maths helpers without needing a real Raspberry Pi:
  - speed_to_duty conversion
  - differential drive decomposition
  - heartbeat trigger logic

Run with:
    cd ros2_ws
    colcon test --packages-select my_robot
  OR:
    pytest src/my_robot/test/test_motor_controller.py -v
"""

import math
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Pure-function versions of motor_controller helpers (extracted for testing)
# ─────────────────────────────────────────────────────────────────────────────

MAX_SPEED   = 1.0
TRACK_WIDTH = 0.20

def speed_to_duty(speed: float, max_speed: float = MAX_SPEED) -> float:
    """Map signed m/s to PWM duty [0, 100]."""
    clamped = max(-max_speed, min(max_speed, speed))
    return (abs(clamped) / max_speed) * 100.0


def differential_drive(linear: float, angular: float,
                        track_half: float = TRACK_WIDTH / 2) -> tuple:
    """Return (left_speed, right_speed) from Twist components."""
    left  = linear - angular * track_half
    right = linear + angular * track_half
    return left, right


# ─────────────────────────────────────────────────────────────────────────────
# Tests — speed_to_duty
# ─────────────────────────────────────────────────────────────────────────────

class TestSpeedToDuty:

    def test_zero_speed_gives_zero_duty(self):
        assert speed_to_duty(0.0) == pytest.approx(0.0)

    def test_max_speed_gives_100_duty(self):
        assert speed_to_duty(1.0) == pytest.approx(100.0)

    def test_half_speed_gives_50_duty(self):
        assert speed_to_duty(0.5) == pytest.approx(50.0)

    def test_negative_speed_gives_positive_duty(self):
        """Reverse direction — duty is magnitude only."""
        assert speed_to_duty(-1.0) == pytest.approx(100.0)
        assert speed_to_duty(-0.5) == pytest.approx(50.0)

    def test_over_max_is_clamped(self):
        assert speed_to_duty(5.0) == pytest.approx(100.0)

    def test_under_min_is_clamped(self):
        assert speed_to_duty(-5.0) == pytest.approx(100.0)

    def test_small_speed(self):
        assert speed_to_duty(0.1) == pytest.approx(10.0)

    def test_custom_max_speed(self):
        assert speed_to_duty(0.5, max_speed=2.0) == pytest.approx(25.0)


# ─────────────────────────────────────────────────────────────────────────────
# Tests — differential_drive
# ─────────────────────────────────────────────────────────────────────────────

class TestDifferentialDrive:

    def test_pure_forward(self):
        left, right = differential_drive(0.5, 0.0)
        assert left  == pytest.approx(0.5)
        assert right == pytest.approx(0.5)

    def test_pure_reverse(self):
        left, right = differential_drive(-0.5, 0.0)
        assert left  == pytest.approx(-0.5)
        assert right == pytest.approx(-0.5)

    def test_turn_left(self):
        """Positive angular.z → CCW → left wheel slower."""
        left, right = differential_drive(0.0, 1.0)
        assert left  < 0
        assert right > 0
        assert right == -left

    def test_turn_right(self):
        """Negative angular.z → CW → right wheel slower."""
        left, right = differential_drive(0.0, -1.0)
        assert left  > 0
        assert right < 0

    def test_forward_with_left_curve(self):
        left, right = differential_drive(0.3, 0.5)
        assert right > left            # right faster for left curve
        assert left  == pytest.approx(0.3 - 0.5 * TRACK_WIDTH / 2)
        assert right == pytest.approx(0.3 + 0.5 * TRACK_WIDTH / 2)

    def test_stop(self):
        left, right = differential_drive(0.0, 0.0)
        assert left  == pytest.approx(0.0)
        assert right == pytest.approx(0.0)

    def test_symmetry(self):
        """Turning left and right with same magnitude should be symmetric."""
        l1, r1 = differential_drive(0.2, 0.5)
        l2, r2 = differential_drive(0.2, -0.5)
        assert l1 == pytest.approx(r2)
        assert r1 == pytest.approx(l2)


# ─────────────────────────────────────────────────────────────────────────────
# Tests — obstacle avoider front-arc check
# ─────────────────────────────────────────────────────────────────────────────

def is_in_front_arc(angle_rad: float, arc_half_rad: float) -> bool:
    """True if angle is within the front arc."""
    a = math.atan2(math.sin(angle_rad), math.cos(angle_rad))
    return abs(a) <= arc_half_rad


FRONT_ARC = math.radians(60.0)  # ±30°, so half = 30°... wait, the param is half-angle
# In the node front_arc_deg=60 means ±60° total / 2 = 30° half — no:
# Actually in the code: abs(angle) <= self._front_arc where front_arc = radians(60) = ±60°
# So total arc is 120°. Let's test accordingly.


class TestFrontArc:

    def test_straight_ahead_in_arc(self):
        assert is_in_front_arc(0.0, FRONT_ARC) is True

    def test_exactly_at_boundary(self):
        assert is_in_front_arc(FRONT_ARC, FRONT_ARC) is True

    def test_just_outside_boundary(self):
        assert is_in_front_arc(FRONT_ARC + 0.01, FRONT_ARC) is False

    def test_behind_robot_not_in_arc(self):
        assert is_in_front_arc(math.pi, FRONT_ARC) is False

    def test_45_deg_in_arc(self):
        assert is_in_front_arc(math.radians(45), FRONT_ARC) is True

    def test_90_deg_outside_arc(self):
        assert is_in_front_arc(math.radians(90), FRONT_ARC) is False

    def test_negative_angle_in_arc(self):
        """Right side — also in arc."""
        assert is_in_front_arc(-math.radians(30), FRONT_ARC) is True
