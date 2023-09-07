# Observatory Control CLI Documentation

Welcome to the Observatory Control CLI documentation. This guide provides comprehensive information on how to use the CLI to control various observatory equipment and functionality. The documentation is organized into sections based on the equipment and functionality controlled by the CLI.

## Table of Contents

1. [Introduction](#introduction)
   - Overview of the Observatory Control CLI.
   - Prerequisites for using the CLI.

2. [Chiller Control](#chiller-control)
   - [chillerStart](#chillerstart)
   - [chillerStop](#chillerstop)

3. [Camera Control](#camera-control)
   - [setExposure](#setexposure)
   - [tecStart](#tecstart)
   - [tecStop](#tecstop)
   - [tecSetCoeffs](#tecsetcoeffs)
   - [killCameraDaemon](#killcameradaemon)

4. [Observation Scheduling](#observation-scheduling)
   - [generate_supernovae_db](#generate_supernovae_db)

5. [Observatory Startup and Shutdown](#observatory-startup-and-shutdown)
   - [do_startup](#do_startup)
   - [total_shutdown](#total_shutdown)
   - [stow_observatory](#stow_observatory)
   - [total_restart](#total_restart)

## 1. Introduction <a name="introduction"></a>

### Overview

The Observatory Control CLI is a powerful tool that allows you to control various aspects of an observatory, including chiller units, cameras, observation scheduling, and observatory startup and shutdown procedures.

### Prerequisites

Before using the CLI, ensure you have the following prerequisites:

- Python environment with the required dependencies installed.
- Access to the observatory's hardware and systems.
- Basic knowledge of observatory operations.

## 2. Chiller Control <a name="chiller-control"></a>

The Chiller Control section provides commands for controlling chiller units used in the observatory.

### chillerStart

- **Usage**: `chillerStart <temperature_setpoint>`
- **Description**: Starts the chiller unit and sets the temperature setpoint.
- **Parameters**:
  - `<temperature_setpoint>`: The desired temperature setpoint.

### chillerStop

- **Usage**: `chillerStop`
- **Description**: Stops the chiller unit.

## 3. Camera Control <a name="camera-control"></a>

The Camera Control section provides commands for controlling observatory cameras.

### setExposure

- **Usage**: `setExposure <exposure_time> [-n <sensor_address>] [-w | -c]`
- **Description**: Sets the exposure time for observatory cameras.
- **Parameters**:
  - `<exposure_time>`: The exposure time in seconds.
  - `-n <sensor_address>` (optional): Specific sensor addresses.
  - `-w` or `-c` (optional): Selects the winter or summer camera.

### tecStart

- **Usage**: `tecStart [-n <sensor_address>] [-w | -c]`
- **Description**: Starts the Thermal Electric Cooler (TEC) for observatory cameras.
- **Parameters**:
  - `-n <sensor_address>` (optional): Specific sensor addresses.
  - `-w` or `-c` (optional): Selects the winter or summer camera.

### tecStop

- **Usage**: `tecStop [-n <sensor_address>] [-w | -c]`
- **Description**: Stops the Thermal Electric Cooler (TEC) for observatory cameras.
- **Parameters**:
  - `-n <sensor_address>` (optional): Specific sensor addresses.
  - `-w` or `-c` (optional): Selects the winter or summer camera.

### tecSetCoeffs

- **Usage**: `tecSetCoeffs <Kp> <Ki> <Kd> [-n <sensor_address>] [-w | -c]`
- **Description**: Sets the PID coefficients (Proportional-Integral-Derivative) for TEC.
- **Parameters**:
  - `<Kp>`: Proportional coefficient.
  - `<Ki>`: Integral coefficient.
  - `<Kd>`: Derivative coefficient.
  - `-n <sensor_address>` (optional): Specific sensor addresses.
  - `-w` or `-c` (optional): Selects the winter or summer camera.

### killCameraDaemon

- **Usage**: `killCameraDaemon [-w | -c]`
- **Description**: Sends a command to kill the camera daemon.
- **Parameters**:
  - `-w` or `-c` (optional): Selects the winter or summer camera.

## 4. Observation Scheduling <a name="observation-scheduling"></a>

The Observation Scheduling section provides commands for generating observation schedules.

### generate_supernovae_db

- **Usage**: `generate_supernovae_db [source]`
- **Description**: Generates a supernovae observation schedule based on the specified data source (ZTF or Rochester).
- **Parameters**:
  - `source` (optional): Data source for supernovae information (default: ZTF).

## 5. Observatory Startup and Shutdown <a name="observatory-startup-and-shutdown"></a>

The Observatory Startup and Shutdown section provides commands for starting up, shutting down, and stowing the observatory.

### do_startup

- **Usage**: `do_startup [--cameras]`
- **Description**: Starts up the observatory, including optional camera startup.
- **Parameters**:
  - `--cameras` (optional): Start up the cameras.

### total_shutdown

- **Usage**: `total_shutdown`
- **Description**: Shuts down the observatory gracefully.

### stow_observatory

- **Usage**: `stow_observatory [--cameras]`
- **Description**: Stows the observatory based on its current state, including optional camera shutdown.

### total_restart

- **Usage**: `total_restart`
- **Description**: Restarts the observatory by first shutting it down and then starting it up again.

This Observatory Control CLI documentation provides a comprehensive guide to controlling your observatory's equipment and functionality through the command-line interface. For detailed information on each command and practical examples, refer to the corresponding sections above.

## Conclusion

With the Observatory Control CLI, you have the flexibility to manage chiller units, cameras, observation scheduling, and observatory startup and shutdown procedures effectively. Please follow safety protocols and best practices when operating observatory equipment.
