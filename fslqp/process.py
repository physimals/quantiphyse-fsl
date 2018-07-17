"""
Processes for FSL tools

These processes use the wrappers in the fslpy package

FIXME: Is FSLDIR etc being set correctly or do we need to do something in FSL wrappers?

Copyright (c) 2013-2018 University of Oxford
"""

import os
import re
import traceback

import fsl.wrappers as fsl
from fsl.data.image import Image

from quantiphyse.data import QpData, NumpyData, DataGrid
from quantiphyse.processes import Process

_LOAD = "Pickleable replacement for fsl.LOAD special value, hope nobody is daft enough to pass this string as a parameter value"

def qpdata_to_fslimage(qpd):
    """ Convert QpData to fsl.data.Image"""
    return Image(qpd.raw(), name=qpd.name, xform=qpd.grid.affine)

def fslimage_to_qpdata(img, name=None):
    """ Convert fsl.data.Image to QpData """
    if not name: name = img.name
    return NumpyData(img.data, grid=DataGrid(img.shape[:3], img.voxToWorldMat), name=name)

class FslOutputProgress(object):
    """
    Simple file-like object which listens to the output
    of an FSL command and sends each line to a Queue
    """
    def __init__(self, queue):
        self._queue = queue

    def write(self, text):
        """ Handle output from the process - send each line to the queue """
        lines = text.splitlines()
        for line in lines:
            self._queue.put(line)

    def flush(self):
        """ Ignore flush requests """
        pass

def _run_fsl(worker_id, queue, cmd, cmd_args):
    """
    Background process worker function which runs an FSL wrapper command
    
    The majority of this is involved in converting input QpData objects to
    fsl.Image and back again afterwards. This is required because fsl.Image
    is not pickleable and therefore cannot be passed as a multiprocessing 
    parameter. Also, the special fsl.LOAD object is not pickleable either
    so we pass our own special LOAD object (which is just a magic string).
    """
    try:
        # Get the FSL wrapper function from the name of the command
        cmd_fn = getattr(fsl, cmd)

        for key in cmd_args.keys():
            val = cmd_args[key]
            if isinstance(val, QpData):
                cmd_args[key] = qpdata_to_fslimage(val)
            elif val == _LOAD:
                cmd_args[key] = fsl.LOAD

        progress_watcher = FslOutputProgress(queue)
        cmd_result = cmd_fn(log={"stdout" : progress_watcher, "cmd" : progress_watcher}, **cmd_args)

        ret = {}
        for key in cmd_result.keys():
            val = cmd_result[key]
            if isinstance(val, Image):
                ret[key] = fslimage_to_qpdata(val, key)
                
        return worker_id, True, ret
    except Exception as exc:
        traceback.print_exc()
        return worker_id, False, exc

class FslProcess(Process):
    """
    Generic FSL process
    """
    PROCESS_NAME = "FslProgram"

    def __init__(self, ivm, **kwargs):
        Process.__init__(self, ivm, worker_fn=_run_fsl, **kwargs)
        path = []
        if "FSLDIR" in os.environ:
            path.append(os.path.join(os.environ["FSLDIR"], "bin"))
        if "FSLDEVDIR" in os.environ:
            path.append(os.path.join(os.environ["FSLDEVDIR"], "bin"))
        if "FSLOUTPUTTYPE" not in os.environ:
            os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"

    def run(self, options):
        """
        Run an FSL wrapper command
        """
        # Reset expected output - this can be updated in init_cmd
        self._output_data = {}
        self._output_rois = {}
        self._expected_steps = []
        self._current_step = 0
        self._current_data = None
        self._current_roi = None

        # Get the command to run and it's arguments (as a dict)
        cmd, cmd_args = self.init_cmd(options)

        # Run as background process
        args = [cmd, cmd_args]
        self.debug(args)
        self.start_bg(args, n_workers=1)

    def init_cmd(self, options):
        """
        Initialise the FSL command, arguments and expected output

        Default implementation takes command and arguments from
        options
        """
        return options.pop("cmd"), options.pop("cmd-args", {})

    def finished(self):
        """
        Add expected output to the IVM and set current data/roi
        """
        self.debug("finished: %i", self.status)
        if self.status == Process.SUCCEEDED:

            cmd_result = self.worker_output[0]
            self.debug(cmd_result)

            self.debug(self._output_data)
            self.debug(self._output_rois)
            for key, qpdata in cmd_result.items():
                self.debug("Looking for mapping for result labelled %s", key)
                if key in self._output_data:
                    self.debug("Found in data: %s", self._output_data[key])
                    self.ivm.add_data(qpdata, name=self._output_data[key])
                if key in self._output_rois:
                    self.debug("Found in rois: %s", self._output_rois[key])
                    self.ivm.add_roi(qpdata, name=self._output_rois[key])

            if self._current_data:
                self.ivm.set_current_data(self._current_data)
                
            if self._current_roi:
                self.ivm.set_current_roi(self._current_roi)
            
    def timeout(self):
        """
        Check the command output on the queue and if it matches
        an expected step, send sig_progress
        """
        if self.queue.empty(): return
        while not self.queue.empty():
            line = self.queue.get()
            self.debug(line)
            if self._current_step < len(self._expected_steps):
                expected = self._expected_steps[self._current_step]
                if expected is not None and re.match(expected, line):
                    self._current_step += 1
                    complete = float(self._current_step) / (len(self._expected_steps)+1)
                    self.debug(complete)
                    self.sig_progress.emit(complete)

class FastProcess(FslProcess):
    """
    FslProcess for the FAST command
    """
    PROCESS_NAME = "Fast"

    def init_cmd(self, options):
        data = self.get_data(options)

        if options.pop("output-pve", True):
            for classnum in range(options["class"]):
                self._output_data["out_pve_%i" % classnum] = "%s_pve_%i" % (data.name, classnum)
            self._current_data = "%s_pve_0" % data.name
        
        if options.pop("output-pveseg", True):
            self._output_rois["out_pveseg"] = "%s_pveseg" % data.name
            self._current_roi = self._output_rois["out_pveseg"]

        if options.pop("output-rawseg", False):
            self._output_rois["out_seg"] = "%s_seg" % data.name 

        if options.pop("output-mixeltype", False):
            self._output_rois["out_mixeltype"] = "%s_mixeltype" % data.name

        if options.pop("biasfield", False):
            options["b"] = True
            self._output_data["out_bias"] = "%s_bias" % data.name

        if options.pop("biascorr", False):
            options["B"] = True
            self._output_data["out_restore"] = "%s_restore" % data.name
        
        self._expected_steps = ["Tanaka Iteration",] * (options.pop("iter") + options.pop("fixed"))

        options.update({"verbose" : True, "imgs" : data, "out" : _LOAD})
        return "fast", options
        
class BetProcess(FslProcess):
    """
    FslProcess for the 'BET' brain extraction tool
    """
    PROCESS_NAME = "Bet"

    def init_cmd(self, options):
        data = self.get_data(options)
        
        cmd_args = {
            "input" : data,
            "output" : _LOAD,
            "fracintensity" : options.pop("thresh", 0.5),
            "seg" : "output-brain" in options,
            "mask" : "output-mask" in options,
            "centre" : options.pop("centre", None),
            "r" : options.pop("radius", None),
        }
        
        if cmd_args["seg"]:
            self._output_data["output"] = options.pop("output-brain")
            self._current_data = self._output_data["output"]
        if cmd_args["mask"]:
            self._output_rois["output_mask"] = options.pop("output-mask")
            self._current_roi = self._output_rois["output_mask"]

        return "bet", cmd_args
