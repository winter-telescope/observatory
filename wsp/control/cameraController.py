# cameraController.py


from transitions import Machine, State

class CameraController:
    """
    Wraps low‑level camera driver calls AND owns its own FSM.
    Public methods such as .start_up(), .warm_up(), .expose(),
    .set_active_mode() are *called* by the master FSM.
    """
    def __init__(self, name, hw_if):
        self.name   = name          # e.g. "winter", "andor1"
        self.hw     = hw_if         # a driver or SDK wrapper
        self.state  = None          # filled by Machine

        cam_states = [
            State("off"),
            State("starting",  on_enter=["_cmd_startup"]),
            State("cooling", on_enter=["_cmd_cooldown"])
            State("ready"),
            State("observing", on_enter=["_cmd_prepare_for_obs"],
                               on_exit=["_cmd_wrap_obs"]),
            State("warming",   on_enter=["_cmd_warmup"]),
        ]

        self.fsm = Machine(
            model=self, states=cam_states, initial="off",
            after_state_change=self._notify_master   # Qt signal or callback
        )
        self.fsm.add_transition("startup",   "off",       "starting")
        self.fsm.add_transition("boot_ok",   "starting",  "ready",
                                conditions=["cooled_and_stable"])
        self.fsm.add_transition("begin_obs", "ready",     "observing")
        self.fsm.add_transition("end_obs",   "observing", "ready")
        self.fsm.add_transition("warm",      ["ready","observing"], "warming")
        self.fsm.add_transition("cool_off",  "warming",   "off")

    # ------------------------------------------------------------------
    # hardware helpers
    # ------------------------------------------------------------------
    def cooled_and_stable(self):
        return self.hw.is_tec_at_setpoint()

    def _cmd_startup(self):
        self.hw.power_on()
        self.hw.start_cooling()

    def _cmd_prepare_for_obs(self):
        self.hw.set_observing_defaults()

    def _cmd_wrap_obs(self):
        self.hw.flush_buffers()

    def _cmd_warmup(self):
        self.hw.stop_cooling()

    def _notify_master(self):
        """
        Called after every camera‐state change.  You can emit a Qt signal or
        call a registered callback so the master controller can react.
        """
        pass
