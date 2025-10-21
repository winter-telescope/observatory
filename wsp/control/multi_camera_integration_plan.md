# Integration Plan for Multi-Camera State Machine into RoboOperator

## Phase 1: Add State Machine Alongside Existing Code

First, add the state machine as a new component that can be toggled on/off:

```python
class RoboOperator(QtCore.QObject):
    def __init__(self, ...):
        # ... existing init code ...
        
        # Multi-camera support flag
        self.multi_camera_enabled = self.config.get('multi_camera_enabled', False)
        
        if self.multi_camera_enabled:
            # Initialize multi-camera state machine
            from multi_camera_state_machine import MultiCameraStateMachine, CameraInfo
            
            # Define available cameras from config
            camera_configs = []
            for camname in self.camdict.keys():
                if camname in self.config.get('multi_camera_config', {}):
                    cam_config = self.config['multi_camera_config'][camname]
                    camera_configs.append(
                        CameraInfo(
                            name=camname,
                            port=cam_config['port'],
                            filters=list(self.config['filters'][camname].keys()),
                            cal_interval_hours=cam_config.get('cal_interval_hours', 1.0),
                            focus_interval_hours=cam_config.get('focus_interval_hours', 2.0)
                        )
                    )
            
            self.state_machine = MultiCameraStateMachine(self, camera_configs)
            
        # Keep existing single camera setup
        self.camname = "winter"
        self.switchCamera(self.camname)
```

## Phase 2: Modify checkWhatToDo to Delegate

Replace the main control method to optionally use state machine:

```python
def checkWhatToDo(self):
    """Main control loop - delegates to state machine if multi-camera enabled"""
    
    if self.multi_camera_enabled:
        # Use new state machine
        self.state_machine.checkWhatToDo()
    else:
        # Use existing implementation
        self._checkWhatToDo_legacy()

def _checkWhatToDo_legacy(self):
    """Original checkWhatToDo implementation"""
    # Move existing checkWhatToDo code here
    # ... (lines 1386-2037) ...
```

## Phase 3: Extend Schedule Loading

Modify the schedule loading to support camera selection:

```python
def load_best_observing_target(self, obstime_mjd):
    """Extended to support camera selection in schedule"""
    # ... existing code ...
    
    # When creating currentObs dict, add camera selection
    if self.multi_camera_enabled:
        # Add logic to select camera based on filter
        if 'camera' not in currentObs:
            # Auto-select camera based on filter
            filter_id = currentObs.get('filter')
            camera_name = self._select_camera_for_filter(filter_id)
            currentObs['camera'] = camera_name
    
    # ... rest of existing code ...

def _select_camera_for_filter(self, filter_id):
    """Select best camera for given filter"""
    for camname, cam_filters in self.config['filters'].items():
        if filter_id in cam_filters:
            # Check if camera is ready (only in multi-camera mode)
            if self.multi_camera_enabled:
                if self.state_machine.camera_status[camname].ready:
                    return camname
            else:
                return camname
    return None
```

## Phase 4: Add Camera Port Switching

Add port switching capability without breaking existing code:

```python
def switch_telescope_port(self, port):
    """Switch telescope to specified camera port"""
    if not hasattr(self, 'current_telescope_port'):
        self.current_telescope_port = None
    
    if self.current_telescope_port != port:
        self.log(f"Switching telescope to port {port}")
        self.doTry(f"telescope_select_port {port}")
        self.current_telescope_port = port
        time.sleep(5)  # Wait for switch to complete

def switchCamera(self, camname):
    """Extended to handle port switching"""
    try:
        camera = self.camdict[camname]
        fw = self.fwdict[camname]
        
        # If multi-camera enabled, switch ports
        if self.multi_camera_enabled and camname in self.config.get('multi_camera_config', {}):
            port = self.config['multi_camera_config'][camname]['port']
            self.switch_telescope_port(port)
        
        # Original camera switching logic
        self.camera = camera
        self.fw = fw
        self.camname = camname
        msg = f"switched roboOperator's camera to {self.camname}"
        
    except Exception as e:
        msg = f"could not switch camera to {camname}: {e}"
    
    self.log(msg)
```

## Phase 5: Extend Camera Status Methods

Make camera status methods multi-camera aware:

```python
def get_camera_ready_status(self, camname=None):
    """Check if camera(s) ready - works for single or multi camera"""
    if self.multi_camera_enabled:
        if camname:
            # Check specific camera
            return self.state_machine.camera_status[camname].ready
        else:
            # Check if any camera is ready
            return any(status.ready for status in self.state_machine.camera_status.values())
    else:
        # Original single camera logic
        if camname and camname != self.camname:
            return False
        return self.get_winter_camera_ready_to_observe_status()
```

## Configuration File Addition

Add to your config file:

```json
{
    "multi_camera_enabled": false,  // Set to true to enable
    "multi_camera_config": {
        "winter": {
            "port": 1,
            "cal_interval_hours": 1.0,
            "focus_interval_hours": 2.0
        },
        "summer": {
            "port": 2,
            "cal_interval_hours": 1.0,
            "focus_interval_hours": 2.0
        },
        "spring": {
            "port": 3,
            "cal_interval_hours": 24.0,
            "focus_interval_hours": 24.0
        }
    }
}
```

## Testing Strategy

1. **Phase 1**: Deploy with `multi_camera_enabled: false` - no change in behavior
2. **Phase 2**: Test with single camera in multi-camera mode
3. **Phase 3**: Test with multiple cameras in controlled environment
4. **Phase 4**: Full deployment with all cameras

## Key Advantages

1. **No Breaking Changes**: Existing code continues to work
2. **Gradual Migration**: Can test incrementally
3. **Rollback Capability**: Can disable with config flag
4. **Maintains Compatibility**: All existing methods/signals preserved