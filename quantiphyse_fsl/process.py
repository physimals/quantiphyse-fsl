"""
Processes for FSL tools

These processes use the wrappers in the fslpy package

FIXME: Is FSLDIR etc being set correctly or do we need to do something in FSL wrappers?

Copyright (c) 2013-2018 University of Oxford
"""

import os
import re
import traceback

import numpy as np

from quantiphyse.data import QpData, NumpyData, DataGrid
from quantiphyse.processes import Process
from quantiphyse.utils import QpException
from quantiphyse.utils.cmdline import OutputStreamMonitor

_LOAD = "Pickleable replacement for fsl.wrappers.LOAD special value, hope nobody is daft enough to pass this string as a parameter value"

def qpdata_to_fslimage(qpd):
    """ Convert QpData to fsl.data.Image"""
    from fsl.data.image import Image
    return Image(qpd.raw(), name=qpd.name, xform=qpd.grid.affine)

def fslimage_to_qpdata(img, name=None, vol=None, region=None):
    """ Convert fsl.data.Image to QpData """
    if not name: name = img.name
    if vol is not None:
        data = img.data[..., vol]
    else:
        data = img.data
    if region is not None:
        data = (data == region).astype(np.int)
    return NumpyData(data, grid=DataGrid(img.shape[:3], img.voxToWorldMat), name=name)

def _run_fsl(worker_id, queue, fsldir, fsldevdir, cmd, cmd_args):
    """
    Background process worker function which runs an FSL wrapper command
    
    The majority of this is involved in converting input QpData objects to
    fsl.Image and back again afterwards. This is required because fsl.Image
    is not pickleable and therefore cannot be passed as a multiprocessing 
    parameter. Also, the special fsl.LOAD object is not pickleable either
    so we pass our own special LOAD object (which is just a magic string).
    """
    try:
        from fsl.data.image import Image
        import fsl.wrappers as fslwrap
        if "FSLOUTPUTTYPE" not in os.environ:
            os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"
        if fsldir:
            os.environ["FSLDIR"] = fsldir
        if fsldevdir:
            os.environ["FSLDEVDIR"] = fsldevdir

        # Get the FSL wrapper function from the name of the command
        cmd_fn = getattr(fslwrap, cmd)
        
        for key in cmd_args.keys():
            val = cmd_args[key]
            if isinstance(val, QpData):
                cmd_args[key] = qpdata_to_fslimage(val)
            elif val == _LOAD:
                cmd_args[key] = fslwrap.LOAD

        progress_watcher = OutputStreamMonitor(queue)
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
        fsldir, fsldevdir = None, None
        if "FSLDIR" in os.environ:
            fsldir = os.environ["FSLDIR"]
        if "FSLDEVDIR" in os.environ:
            fsldevdir = os.environ["FSLDEVDIR"]
        cmd, cmd_args = self.init_cmd(options)

        # Run as background process
        args = [fsldir, fsldevdir, cmd, cmd_args]
        self.debug(args)
        self.start_bg(args, n_workers=1)

    def init_cmd(self, options):
        """
        Initialise the FSL command, arguments and expected output

        Default implementation takes command and arguments from
        options
        """
        return options.pop("cmd"), options.pop("cmd-args", {})

    def finished(self, worker_output):
        """
        Add expected output to the IVM and set current data/roi
        """
        self.debug("finished: %i", self.status)
        if self.status == Process.SUCCEEDED:

            cmd_result = worker_output[0]
            self.debug(cmd_result)

            self.debug(self._output_data)
            for key, qpdata in cmd_result.items():
                self.debug("Looking for mapping for result labelled %s", key)
                if key in self._output_data:
                    self.debug("Found in data: %s", self._output_data[key])
                    qpdata.roi = False
                    self.ivm.add(qpdata, name=self._output_data[key])
                if key in self._output_rois:
                    self.debug("Found in ROIs: %s", self._output_rois[key])
                    qpdata.roi = True
                    self.ivm.add(qpdata, name=self._output_rois[key])

            if self._current_data:
                self.ivm.set_current_data(self._current_data)
                
            if self._current_roi:
                self.ivm.set_current_roi(self._current_roi)
            
    def timeout(self, queue):
        """
        Check the command output on the queue and if it matches
        an expected step, send sig_progress
        """
        if queue.empty(): return
        while not queue.empty():
            line = queue.get()
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
        
        self._expected_steps = ["Tanaka Iteration",] * (options.pop("iter", 4) + options.pop("fixed", 4))

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

class FslAnatProcess(FslProcess):
    """
    FslProcess for the 'FSL_ANAT' tool
    """
    PROCESS_NAME = "FslAnat"

    def init_cmd(self, options):
        data = self.get_data(options)
        
        cmd_args = {
            "img" : data,
            "out" : _LOAD,
        }
        cmd_args.update(options)

        self._output_data = {
            #'out.anat/MNI_to_T1_nonlin_field' : '',
            #'out.anat/MNI152_T1_2mm_brain_mask_dil1' : '',
            #'out.anat/T1_to_MNI_lin' : '',
            #'out.anat/T1_to_MNI_nonlin' : '',
            #'out.anat/T1_to_MNI_nonlin_jac' : '',
            #'out.anat/T1_to_MNI_nonlin_field' : '',
            #'out.anat/T1_to_MNI_nonlin_coeff' : '',
            #'out.anat/lesionmask' : '',
            #'out.anat/lesionmaskinv' : '',
        }
        if not options.get("nosubcortseg", False):
            self._output_data.update({
                'out.anat/T1' : data.name + '_crop',
                #'out.anat/T1_fullfov' : '',
            })

        if not options.get("nobias", False):
            self._output_data.update({
                'out.anat/T1_biascorr' : data.name + '_biascorr',
                'out.anat/T1_biascorr_brain' : data.name + '_brain',
                'out.anat/T1_biascorr_brain_mask' : data.name + '_brain_mask',
                #'out.anat/T1_biascorr_bet_skull' : data.name + '_skull,
                'out.anat/T1_fast_bias' : data.name + '_bias',
            })

        if not options.get("noseg", False):
            self._output_data.update({
                'out.anat/T1_fast_pve_0' : data.name + '_pve_0',
                'out.anat/T1_fast_pve_1' : data.name + '_pve_1',
                'out.anat/T1_fast_pve_2' : data.name + '_pve_2',
                #'out.anat/T1_fast_restore' : '',
            })
            self._output_rois.update({
                'out.anat/T1_fast_seg' : data.name + '_seg',
                'out.anat/T1_fast_pveseg' : data.name + '_pveseg',
                'out.anat/T1_fast_mixeltype' : data.name + '_mixeltype',
            })

        if not options.get("nosubcortseg", False):
            self._output_rois.update({
                'out.anat/T1_subcort_seg': data.name + '_subcort_seg',
                #'out.anat/first_results/T1_first_all_fast_firstseg' : '',
                #'out.anat/first_results/T1_first_all_fast_origsegs': '',
            })

        self._expected_steps = ["Single Image Segmentation", "tissue-type segmentation"]

        return "fsl_anat", cmd_args

class FslMathsProcess(Process):
    """
    FslProcess for the 'FSL_ANAT' tool
    """
    PROCESS_NAME = "FslMaths"

    def run(self, options):
        from fsl.wrappers import fslmaths
        
        cmds = options.pop("cmd", "").split()
        if cmds[0] == "fslmaths":
            del cmds[0]

        input_data = cmds[0]
        output_data = cmds[-1]
        if input_data not in self.ivm.data:
            raise QpException("Input data not found: %s" % input_data)
        
        cmds = cmds[1:-1]
        img = qpdata_to_fslimage(self.ivm.data[input_data])
        proc = fslmaths(img)
        current_method = None
        current_args = []
        for cmd in cmds:
            if cmd[0] == "-":
                if current_method is not None:
                    self.debug("Executing %s(%s)", current_method, current_args)
                    proc = current_method(*current_args)
                elif current_args:
                    self.warn("Discarding args: %s", current_args)
                cmd = cmd.lstrip("-")
                try:
                    current_method = getattr(proc, cmd)
                except AttributeError:
                    self.warn("No such command")
                    current_method = None
                current_args = []
            else:
                if cmd in self.ivm.data:
                    current_args.append(qpdata_to_fslimage(self.ivm.data[cmd]))
                else:
                    current_args.append(cmd)

        if current_method is not None:
            self.debug("Executing %s(%s)", current_method, current_args)
            proc = current_method(*current_args)
        ret = proc.run()
        self.ivm.add(fslimage_to_qpdata(ret), name=output_data)
