#####################################################################
#                                                                   #
# /labscript_devices/IMAQdxCamera/labscript_devices.py              #
#                                                                   #
# Copyright 2019, Monash University and contributors                #
#                                                                   #
# This file is part of labscript_devices, in the labscript suite    #
# (see http://labscriptsuite.org), and is licensed under the        #
# Simplified BSD License. See the license.txt file in the root of   #
# the project for the full license.                                 #
#                                                                   #
#####################################################################
import sys
from labscript_utils import dedent
from labscript import TriggerableDevice, set_passed_properties, AnalogOut,Device
import numpy as np
import labscript_utils.h5_lock
import h5py


class AnalogTriggerableDevice(Device):
    trigger_edge_type = 'rising'
    minimum_recovery_time = 0
    # A class devices should inherit if they do
    # not require a pseudoclock, but do require a trigger.
    # This enables them to have a Trigger device as a parent
    
    @set_passed_properties(property_names = {})
    def __init__(self, name, parent_device, connection, voltage, parentless=False, **kwargs):

        if None in [parent_device, connection] and not parentless:
            raise LabscriptError('No parent specified. If this device does not require a parent, set parentless=True')
        if isinstance(parent_device, AnalogTrigger):
            if self.trigger_edge_type != parent_device.trigger_edge_type:
                raise LabscriptError('Trigger edge type for %s is \'%s\', ' % (name, self.trigger_edge_type) + 
                                      'but existing Trigger object %s ' % parent_device.name +
                                      'has edge type \'%s\'' % parent_device.trigger_edge_type)
            self.trigger_device = parent_device
        elif parent_device is not None:
            # Instantiate a trigger object to be our parent:
            self.trigger_device = AnalogTrigger(name + '_trigger', parent_device, connection, voltage, self.trigger_edge_type)
            parent_device = self.trigger_device
            connection = 'trigger'
            
        self.__triggers = []
        Device.__init__(self, name, parent_device, connection, **kwargs)

    def trigger(self, t, duration):
        """Request parent trigger device to produce a trigger at time t with given
        duration."""
        # Only ask for a trigger if one has not already been requested by another device
        # attached to the same trigger:
        already_requested = False
        for other_device in self.trigger_device.child_devices:
            if other_device is not self:
                for other_t, other_duration in other_device.__triggers:
                    if t == other_t and duration == other_duration:
                        already_requested = True
        if not already_requested:
            self.trigger_device.trigger(t, duration)

        # Check for triggers too close together (check for overlapping triggers already
        # performed in Trigger.trigger()):
        start = t
        end = t + duration
        for other_t, other_duration in self.__triggers:
            other_start = other_t
            other_end = other_t + other_duration
            if (
                abs(other_start - end) < self.minimum_recovery_time
                or abs(other_end - start) < self.minimum_recovery_time
            ):
                msg = """%s %s has two triggers closer together than the minimum
                    recovery time: one at t = %fs for %fs, and another at t = %fs for
                    %fs. The minimum recovery time is %fs."""
                msg = msg % (
                    self.description,
                    self.name,
                    t,
                    duration,
                    start,
                    duration,
                    self.minimum_recovery_time,
                )
                raise ValueError(dedent(msg))

        self.__triggers.append([t, duration])

    def do_checks(self):
        # Check that all devices sharing a trigger device have triggers when we have triggers:
        for device in self.trigger_device.child_devices:
            if device is not self:
                for trigger in self.__triggers:
                    if trigger not in device.__triggers:
                        start, duration = trigger
                        raise LabscriptError('TriggerableDevices %s and %s share a trigger. ' % (self.name, device.name) + 
                                             '%s has a trigger at %fs for %fs, ' % (self.name, start, duration) +
                                             'but there is no matching trigger for %s. ' % device.name +
                                             'Devices sharing a trigger must have identical trigger times and durations.')

    def generate_code(self, hdf5_file):
        self.do_checks()
        Device.generate_code(self, hdf5_file)
### Define AnalogTrigger class here for replacing Trigger(DigitalOut) instance.
class AnalogTrigger(AnalogOut):
    description = 'analog trigger device'
    allowed_states = {1:'high', 0:'low'}
    allowed_children = [AnalogTriggerableDevice]
    voltage = 0
    def go_high_analog(self,t):
        self.constant(t,self.voltage)
    def go_low_analog(self,t):
        self.constant(t,0)

    @set_passed_properties(property_names = {})
    def __init__(self, name, parent_device, connection, voltage, trigger_edge_type='rising',
                 **kwargs):

        AnalogOut.__init__(self,name,parent_device,connection, **kwargs)
        
        self.trigger_edge_type = trigger_edge_type
        if self.trigger_edge_type == 'rising':
            self.enable = self.go_high_analog
            self.disable = self.go_low_analog
            self.allowed_states = {1:'enabled', 0:'disabled'}
        elif self.trigger_edge_type == 'falling':
            self.enable = self.go_low_analog
            self.disable = self.go_high_analog
            self.allowed_states = {1:'disabled', 0:'enabled'}
        else:
            raise ValueError('trigger_edge_type must be \'rising\' or \'falling\', not \'%s\'.'%trigger_edge_type)
        # A list of the times this trigger has been asked to trigger:
        self.triggerings = []
        
        
    def trigger(self, t, duration):
        assert duration > 0, "Negative or zero trigger duration given"
        if t != self.t0 and self.t0 not in self.instructions:
            self.disable(self.t0)
        
        start = t
        end = t + duration
        for other_start, other_duration in self.triggerings:
            other_end = other_start + other_duration
            # Check for overlapping exposures:
            if not (end < other_start or start > other_end):
                raise LabscriptError('%s %s has two overlapping triggerings: ' %(self.description, self.name) + \
                                     'one at t = %fs for %fs, and another at t = %fs for %fs.'%(start, duration, other_start, other_duration))
        self.enable(t)
        self.disable(round(t + duration,10))
        self.triggerings.append((t, duration))

    def add_device(self, device):
        if not device.connection == 'trigger':
            raise LabscriptError('The \'connection\' string of device %s '%device.name + 
                                 'to %s must be \'trigger\', not \'%s\''%(self.name, repr(device.connection)))
        AnalogOut.add_device(self, device)


class AnalogIMAQdxCamera(AnalogTriggerableDevice):
    description = 'Analog IMAQdx Camera'

    @set_passed_properties(
        property_names={
            "connection_table_properties": [
                "serial_number",
                "orientation",
                "manual_mode_camera_attributes",
                "mock",
            ],
            "device_properties": [
                "camera_attributes",
                "stop_acquisition_timeout",
                "exception_on_failed_shot",
                "saved_attribute_visibility_level"
            ],
        }
    )
    def __init__(
        self,
        name,
        parent_device,
        connection,
        serial_number,
        voltage=1,
        orientation=None,
        trigger_edge_type='rising',
        trigger_duration=None,
        minimum_recovery_time=0.0,
        camera_attributes=None,
        manual_mode_camera_attributes=None,
        stop_acquisition_timeout=5.0,
        exception_on_failed_shot=True,
        saved_attribute_visibility_level='intermediate',
        mock=False,
        **kwargs
    ):
        """A camera to be controlled using NI IMAQdx and triggered with a digital edge.

        Args:
            name (str)
                device name

            parent_device (IntermediateDevice)
                Device with digital outputs to be used to trigger acquisition

            connection (str)
                Name of digital output port on parent device.

            serial_number (str or int)
                string or integer (integer allows entering a hex literal) of the
                camera's serial number. This will be used to idenitfy the camera.

            orientation (str, optional), default: `<name>`
                Description of the camera's location or orientation. This will be used
                to determine the location in the shot file where the images will be
                saved. If not given, the device name will be used instead.

            trigger_edge_type (str), default: `'rising'`
                The direction of the desired edges to be generated on the parent
                devices's digital output used for triggering. Must be 'rising' or
                'falling'. Note that this only determines the edges created on the
                parent device, it does not program the camera to expect this type of
                edge. If required, one must configure the camera separately via
                `camera_attributes` to ensure it expects the type of edge being
                generated. Default: `'rising'`

            trigger_duration (float or None), default: `None`
                Duration of digital pulses to be generated by the parent device. This
                can also be specified as an argument to `expose()` - the value given
                here will be used only if nothing is passed to `expose()`.

            minimum_recovery_time (float), default: `0`
                Minimum time between frames. This will be used for error checking during
                compilation.

            camera_attributes (dict, optional):
                Dictionary of camera attribute names and values to be programmed into
                the camera. The meaning of these attributes is model-specific.
                Attributes will be programmed in the order they appear in this
                dictionary. This can be important as some attributes may not be settable
                unless another attrbiute has been set first. After adding this device to
                your connection table, a dictionary of the camera's default attributes
                can be obtained from the BLACS tab, appropriate for copying and pasting
                into your connection table to customise the ones you are interested in.

            manual_mode_camera_attributes (dict, optional):
                Dictionary of attributes that will be programmed into the camera during
                manual mode, that differ from their values in `camera_attributes`. This
                can be useful for example, to have software triggering during manual
                mode (allowing the acquisition of frames from the BLACS manual mode
                interface) but hardware triggering during buffered runs. Any attributes
                in this dictionary must also be present in `camera_attributes`.

            stop_acquisition_timeout (float), default: `5.0`
                How long, in seconds, to wait during `transition_to_buffered` for the
                acquisition of images to complete before giving up. Whilst all triggers
                should have been received, this can be used to allow for slow image
                download time.

            exception_on_failed_shot (bool), default: `True`.
                If acquisition does not complete within the given timeout after the end
                of a shot, whether to raise an exception. If False, instead prints a
                warning to stderr (visible in the terminal output pane in the BLACS
                tab), saves the images acquired so far, and continues. In the case of
                such a 'failed shot', the HDF5 attribute
                f['images'][orientation/name].attrs['failed_shot'] will be set to `True`
                (otherwise it is set to `False`). This attribute is acessible in the
                lyse dataframe as `df[orientation/name, 'failed_shot']`.

            saved_attribute_visibility_level (str or None), default: 'intermediate'
                The detail level of the camera attributes saved to the HDF5 file at the
                end of each shot. If None, no attributes will be saved. Must be one of
                `'simple'`, `'intermediate'`, `'advanced'`, or `None`. If `None`, no
                attributes will be saved.

            mock (bool, optional), default: False
                For testing purpses, simulate a camera with fake data instead of
                communicating with actual hardware.

            **kwargs: Further keyword arguments to be passed to the `__init__` method of
                the parent class (TriggerableDevice).
        """
        self.trigger_edge_type = trigger_edge_type
        self.minimum_recovery_time = minimum_recovery_time
        self.trigger_duration = trigger_duration
        self.orientation = orientation
        if isinstance(serial_number, (str, bytes)):
            serial_number = int(serial_number, 16)
        self.serial_number = serial_number
        self.BLACS_connection = hex(self.serial_number)[2:].upper()
        if camera_attributes is None:
            camera_attributes = {}
        if manual_mode_camera_attributes is None:
            manual_mode_camera_attributes = {}
        for attr_name in manual_mode_camera_attributes:
            if attr_name not in camera_attributes:
                msg = f"""attribute '{attr_name}' is present in
                    manual_mode_camera_attributes but not in camera_attributes.
                    Attributes that are to differ between manual mode and buffered
                    mode must be present in both dictionaries."""
                raise ValueError(dedent(msg))
        valid_attr_levels = ('simple', 'intermediate', 'advanced', None)
        if saved_attribute_visibility_level not in valid_attr_levels:
            msg = "saved_attribute_visibility_level must be one of %s"
            raise ValueError(msg % valid_attr_levels)
        self.camera_attributes = camera_attributes
        self.manual_mode_camera_attributes = manual_mode_camera_attributes
        self.exposures = []
        ### TriggerableDevice is where the Trigger class is instantiated. 
        ### The Trigger class 
        AnalogTriggerableDevice.__init__(self, name, parent_device, connection,voltage, **kwargs)

    def expose(self, t, name, frametype='frame', trigger_duration=None):
        """Request an exposure at the given time. A trigger will be produced by the
        parent trigger object, with duration trigger_duration, or if not specified, of
        self.trigger_duration. The frame should have a `name, and optionally a
        `frametype`, both strings. These determine where the image will be stored in the
        hdf5 file. `name` should be a description of the image being taken, such as
        "insitu_absorption" or "fluorescence" or similar. `frametype` is optional and is
        the type of frame being acquired, for imaging methods that involve multiple
        frames. For example an absorption image of atoms might have three frames:
        'probe', 'atoms' and 'background'. For this one might call expose three times
        with the same name, but three different frametypes.
        """
        # Backward compatibility with code that calls expose with name as the first
        # argument and t as the second argument:
        if isinstance(t, str) and isinstance(name, (int, float)):
            msg = """expose() takes `t` as the first argument and `name` as the second
                argument, but was called with a string as the first argument and a
                number as the second. Swapping arguments for compatibility, but you are
                advised to modify your code to the correct argument order."""
            print(dedent(msg), file=sys.stderr)
            t, name = name, t
        if trigger_duration is None:
            trigger_duration = self.trigger_duration
        if trigger_duration is None:
            msg = """%s %s has not had an trigger_duration set as an instantiation
                argument, and none was specified for this exposure"""
            raise ValueError(dedent(msg) % (self.description, self.name))
        if not trigger_duration > 0:
            msg = "trigger_duration must be > 0, not %s" % str(trigger_duration)
            raise ValueError(msg)
        self.trigger(t, trigger_duration)
        self.exposures.append((t, name, frametype, trigger_duration))
        return trigger_duration

    def generate_code(self, hdf5_file):
        self.do_checks()
        vlenstr = h5py.special_dtype(vlen=str)
        table_dtypes = [
            ('t', float),
            ('name', vlenstr),
            ('frametype', vlenstr),
            ('trigger_duration', float),
        ]
        data = np.array(self.exposures, dtype=table_dtypes)
        group = self.init_device_group(hdf5_file)
        if self.exposures:
            group.create_dataset('EXPOSURES', data=data)
