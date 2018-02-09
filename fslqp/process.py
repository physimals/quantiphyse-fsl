import os

import numpy as np
import scipy
import sys

from PySide import QtGui

from quantiphyse.volumes.io import save
from quantiphyse.utils.exceptions import QpException
from quantiphyse.utils.cmdline import Workspace

from quantiphyse.analysis import Process

class FslProcess(Process):
    """
    Generic FSL process
    """
    PROCESS_NAME = "FslProgram"

    def __init__(self, ivm, **kwargs):
        Process.__init__(self, ivm, **kwargs)

    def run(self, options):
        argline = options.pop("argline", None)
        if argline is None:
            raise QpException("No command arguments provided")
            
        prog = options.pop("prog", None)
        if prog is None:
            raise QpException("No FSL command provided")

        output_data = options.pop("output-data", {})
        output_rois = options.pop("output-rois", {})
        
        wsp = Workspace(self.ivm)
        wsp.run(prog, argline=argline, output_data=output_data, output_rois=output_rois)
        
        self.status = Process.SUCCEEDED

class FastProcess(FslProcess):
    PROCESS_NAME = "Fast"

    def run(self, options):
        data_name = options.pop("data", None)
        if data_name is None:
            if self.ivm.main is None:
                raise QpException("No data loaded")
            else:
                data_name = self.ivm.main.name

        argline = " ".join(["%s %s" % (k, v) for k, v in options.items() if v not in(True, False)])
        if options.pop("biasfield", False):
            argline += " -b"
        if options.pop("biascorr", False):
            argline += " -B"
        
        argline += " " + data_name
        FslProcess.run(self, {"prog" : "fast", "argline" : argline})

class BetProcess(FslProcess):
    PROCESS_NAME = "Bet"

    def run(self, options):
        data_name = options.pop("data", None)
        if data_name is None:
            if self.ivm.main is None:
                raise QpException("No data loaded")
            else:
                data_name = self.ivm.main.name

        argline = "%s %s_bet -f %f" % (data_name, data_name, options.pop("thresh", 0.5))
        output_data, output_rois = {}, {}
        output_brain = options.pop("output-brain", None)
        if output_brain is not None:
            output_data["%s_bet" % data_name] = output_brain 
        else:
            argline += " -n"

        output_mask = options.pop("output-mask", None)
        if output_mask is not None:
            output_rois["%s_bet_mask" % data_name] = output_mask
            argline += " -m"

        FslProcess.run(self, {"prog" : "bet", "argline" : argline, 
                              "output-data" : output_data, "output-rois" : output_rois})
