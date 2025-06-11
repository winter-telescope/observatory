from 

class RoboController:
    def __init__(self, cam_specs):
        # --------------------------------------------------------------
        # make camera controllers
        # --------------------------------------------------------------
        self.cameras = {
            name: CameraController(name, hw_if)
            for name, hw_if in cam_specs.items()
        }
        self.active_cam = None      # str | None

        # --------------------------------------------------------------
        # master states
        # --------------------------------------------------------------
        master_states = [
            "idle",
            "starting_cameras",
            "waiting_for_night",
            "observing",
            "weather_closure",
            "shutdown",
            "lockout",
            "engineering",
        ]

        self.fsm = Machine(
            model = self,
            states = master_states,
            initial = "idle",
            ignore_invalid_triggers = True
        )

        # --------------------------------------------------------------
        # cadence transitions
        # --------------------------------------------------------------
        self.fsm.add_transition("begin_startup",  "idle", "starting_cameras",
                                after="kick_all_camera_startup")
        self.fsm.add_transition("all_cams_ready", "starting_cameras",
                                "waiting_for_night")

        self.fsm.add_transition("nighttime",      "waiting_for_night",
                                "observing", conditions=["have_ready_cam"])
        self.fsm.add_transition("weather_bad",    "observing",
                                "weather_closure")
        self.fsm.add_transition("weather_good",   "weather_closure",
                                "observing", conditions=["still_dark"])
        self.fsm.add_transition("sunrise",        ["observing",
                                                   "weather_closure"],
                                "shutdown",
                                after="begin_shutdown")
        self.fsm.add_transition("shutdown_done",  "shutdown", "idle")

        # --------------------------------------------------------------
        # camera‑override transitions *inside* OBSERVING
        # --------------------------------------------------------------
        self.fsm.add_transition("switch_camera",  "observing", "observing",
                                before="do_switch_camera",
                                conditions=["target_cam_ready"])

        # overrides (lockout, engineering) omitted here for brevity
    # ------------------------------------------------------------------
    # callbacks
    # ------------------------------------------------------------------
    def kick_all_camera_startup(self):
        for cam in self.cameras.values():
            if cam.state == "off":
                cam.startup()

    def have_ready_cam(self):
        return any(c.state == "ready" for c in self.cameras.values())

    def target_cam_ready(self, cam_name, **_):
        cam = self.cameras.get(cam_name)
        return cam and cam.state == "ready"

    def do_switch_camera(self, cam_name, **_):
        """
        Called whenever operator issues .switch_camera("andor1") while in
        OBSERVING.  Ensures current active cam exits OBSERVING sub‑state,
        then activates the new one.
        """
        if self.active_cam and self.active_cam != cam_name:
            self.cameras[self.active_cam].end_obs()

        self.cameras[cam_name].begin_obs()
        self.active_cam = cam_name
        self._announce(f"Active camera is now **{cam_name}**")

    # ------------------------------------------------------------------
    # camera FSM callbacks come in here
    # ------------------------------------------------------------------
    def camera_state_callback(self, cam_name, new_state):
        """
        Registered as each CameraController’s _notify_master callback.
        Handles cross‑talk: e.g. when last camera enters READY, fire
        all_cams_ready(); when camera fails, go to safe mode; etc.
        """
        if self.state == "starting_cameras":
            if all(c.state == "ready" for c in self.cameras.values()):
                self.all_cams_ready()

    # ------------------------------------------------------------------
    # shutdown sequence
    # ------------------------------------------------------------------
    def begin_shutdown(self):
        for cam in self.cameras.values():
            if cam.state in ("observing", "ready"):
                cam.warm()          # begins warm‑up
        # also close dome etc.
