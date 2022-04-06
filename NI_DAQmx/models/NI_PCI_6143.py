#####################################################################
#                                                                   #
# /NI_DAQmx/models/_subclass_template.py                            #
#                                                                   #
# Copyright 2018, Christopher Billington                            #
#                                                                   #
# This file is part of the module labscript_devices, in the         #
# labscript suite (see http://labscriptsuite.org), and is           #
# licensed under the Simplified BSD License. See the license.txt    #
# file in the root of the project for the full license.             #
#                                                                   #
#####################################################################

#####################################################################
#     WARNING                                                       #
#                                                                   #
# This file is auto-generated, any modifications may be             #
# overwritten. See README.txt in this folder for details            #
#                                                                   #
#####################################################################


from labscript_devices.NI_DAQmx.labscript_devices import NI_DAQmx

#:
CAPABILITIES = {
    'AI_range': [-5.0, 5.0],
    'AI_range_Diff': [-5.0, 5.0],
    'AI_start_delay': 1e-07,
    'AI_term': 'Diff',
    'AI_term_cfg': {
        'ai0': ['Diff'],
        'ai1': ['Diff'],
        'ai2': ['Diff'],
        'ai3': ['Diff'],
        'ai4': ['Diff'],
        'ai5': ['Diff'],
        'ai6': ['Diff'],
        'ai7': ['Diff'],
    },
    'AO_range': None,
    'max_AI_multi_chan_rate': 250000.0,
    'max_AI_single_chan_rate': 250000.0,
    'max_AO_sample_rate': None,
    'max_DO_sample_rate': None,
    'min_semiperiod_measurement': 2e-05,
    'num_AI': 8,
    'num_AO': 0,
    'num_CI': 2,
    'ports': {'port0': {'num_lines': 8, 'supports_buffered': False}},
    'supports_buffered_AO': False,
    'supports_buffered_DO': False,
    'supports_semiperiod_measurement': True,
    'supports_simultaneous_AI_sampling': True,
}


class NI_PCI_6143(NI_DAQmx):
    description = 'NI-PCI-6143'

    def __init__(self, *args, **kwargs):
        """Class for NI-PCI-6143"""
        # Any provided kwargs take precedent over capabilities
        combined_kwargs = CAPABILITIES.copy()
        combined_kwargs.update(kwargs)
        NI_DAQmx.__init__(self, *args, **combined_kwargs)
