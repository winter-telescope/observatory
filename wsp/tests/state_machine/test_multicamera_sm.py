# tests/test_multicamera_sm.py
from wsp.control.multi_camera_state_machine import (
    CameraState,
    ObservatoryState,
)


def test_startup_to_ready_and_observe(fake_robo, state_machine, run_ticks):
    sm = state_machine

    # Tick 1: IDLE -> CHECKING_CAMERAS
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.CHECKING_CAMERAS

    # Tick 2: CHECKING_CAMERAS -> STARTING_CAMERAS (cameras OFF)
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.STARTING_CAMERAS

    # Tick 3: STARTING_CAMERAS -> WAITING_CAMERAS_READY and mark startup requested
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.WAITING_CAMERAS_READY
    assert any(
        s.state == CameraState.STARTUP_REQUESTED for s in sm.camera_status.values()
    )

    # Make the first camera appear autostarted; but autostart_override=True already suffices.
    # Tick 4: WAITING_CAMERAS_READY -> CHECKING_CALS (some camera READY)
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.CHECKING_CALS
    assert any(s.state == CameraState.READY for s in sm.camera_status.values())

    # Tick 5: CHECKING_CALS -> CHECKING_CONDITIONS (no pending cals)
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.CHECKING_CONDITIONS

    # Our fixture routes CHECKING_FOCUS -> SELECTING_TARGET
    # Tick 6: CHECKING_CONDITIONS -> CHECKING_FOCUS
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.CHECKING_FOCUS

    # Tick 7: CHECKING_FOCUS (patched) -> SELECTING_TARGET
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.SELECTING_TARGET

    # Tick 8: SELECTING_TARGET -> SWITCHING_PORT
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.SWITCHING_PORT

    # Tick 9: SWITCHING_PORT -> PREPARING_OBSERVATION (and possibly set current_port)
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.PREPARING_OBSERVATION
    # current_observation should exist
    assert sm.current_observation is not None

    # Tick 10: PREPARING_OBSERVATION -> OBSERVING
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.OBSERVING

    # Tick 11: OBSERVING -> CHECKING_CAMERAS, and obs recorded
    run_ticks(sm, 1)
    assert sm.context.current_state == ObservatoryState.CHECKING_CAMERAS
    assert len(fake_robo.observations_done) >= 1


def test_port_switch_command_emitted(fake_robo, state_machine, run_ticks):
    sm = state_machine

    # Bring at least one camera to READY quickly
    run_ticks(sm, 3)  # IDLE→CHECKING_CAMERAS→STARTING_CAMERAS→WAITING_CAMERAS_READY
    run_ticks(sm, 1)  # WAITING_CAMERAS_READY → CHECKING_CALS
    run_ticks(sm, 2)  # → CHECKING_CONDITIONS → CHECKING_FOCUS (patched)

    # SELECTING_TARGET
    run_ticks(sm, 1)  # CHECKING_FOCUS (patched) → SELECTING_TARGET
    run_ticks(sm, 1)  # SELECTING_TARGET → SWITCHING_PORT

    # On switching, ensure a telescope_select_port command appears
    run_ticks(sm, 1)  # SWITCHING_PORT → PREPARING_OBSERVATION (and port set)
    # Look for the command
    assert any(cmd.startswith("telescope_select_port") for cmd in fake_robo.commands)
    assert isinstance(sm.current_port, int)


def test_error_state_on_action_exception(
    fake_robo, state_machine, monkeypatch, run_ticks
):
    sm = state_machine

    # Drive forward to just before OBSERVING
    run_ticks(sm, 3)  # up to WAITING_CAMERAS_READY
    run_ticks(sm, 1)  # -> CHECKING_CALS
    run_ticks(sm, 2)  # -> CHECKING_CONDITIONS -> CHECKING_FOCUS (patched)
    run_ticks(sm, 1)  # -> SELECTING_TARGET
    run_ticks(sm, 1)  # -> SWITCHING_PORT
    run_ticks(sm, 1)  # -> PREPARING_OBSERVATION
    run_ticks(sm, 1)  # -> OBSERVING

    # Now force do_currentObs to raise
    def boom(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(fake_robo, "do_currentObs", boom)

    # This tick should hit OBSERVING.execute and raise → ERROR → STANDBY
    run_ticks(sm, 1)  # execute in OBSERVING triggers exception
    assert sm.context.current_state in {
        ObservatoryState.ERROR,
        ObservatoryState.STANDBY,
    }
