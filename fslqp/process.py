import os

from quantiphyse.utils.exceptions import QpException
from quantiphyse.utils.cmdline import CommandProcess

class FslProcess(CommandProcess):
    """
    Generic FSL process
    """
    PROCESS_NAME = "FslProgram"

    def __init__(self, ivm, **kwargs):
        path = []
        if "FSLDIR" in os.environ:
            path.append(os.path.join(os.environ["FSLDIR"], "bin"))
        if "FSLDEVDIR" in os.environ:
            path.append(os.path.join(os.environ["FSLDEVDIR"], "bin"))
        if "FSLOUTPUTTYPE" not in os.environ:
            os.environ["FSLOUTPUTTYPE"] = "NIFTI_GZ"

        CommandProcess.__init__(self, ivm, path=path, **kwargs)
        
class FastProcess(FslProcess):
    PROCESS_NAME = "Fast"

    def run(self, options):
        data_name = options.pop("data", None)
        if data_name is None:
            if self.ivm.main is None:
                raise QpException("No data loaded")
            else:
                data_name = self.ivm.main.name

        cmdline = " ".join(["--%s=%s" % (k, v) for k, v in options.items() if type(v) is not bool])
        output_data, output_rois = [], []

        if options.pop("output-pve", True):
            for n in range(options["class"]):
                output_data.append("%s_pve_%i" % (data_name, n))
        
        if options.pop("output-pveseg", True):
            output_rois.append("%s_pveseg" % data_name)

        if options.pop("output-rawseg", False):
            output_rois.append("%s_seg" % data_name)

        if options.pop("output-mixeltype", False):
            output_rois.append("%s_mixeltype" % data_name)

        if options.pop("biasfield", False):
            cmdline += " -b"
            output_data.append("%s_bias" % data_name)

        if options.pop("biascorr", False):
            cmdline += " -B"
            output_data.append("%s_restore" % data_name)
        
        steps =  ["Tanaka Iteration",] * (options.pop("iter") + options.pop("fixed"))

        cmdline += " --verbose " + data_name
        FslProcess.run(self, {
            "cmd" : "fast", 
            "cmdline" : cmdline,
            "output-data" : output_data,
            "output-rois" : output_rois,
            "expected-steps" : steps,
            "set-current-data" : output_data[0],
            "set-current-roi" : output_rois[0],
        })

class BetProcess(FslProcess):
    PROCESS_NAME = "Bet"

    def run(self, options):
        data_name = options.pop("data", None)
        if data_name is None:
            if self.ivm.main is None:
                raise QpException("No data loaded")
            else:
                data_name = self.ivm.main.name

        cmdline = "%s %s_bet -f %f" % (data_name, data_name, options.pop("thresh", 0.5))
        output_data, output_rois = {}, {}
        output_brain = options.pop("output-brain", None)
        if output_brain is not None:
            output_data["%s_bet" % data_name] = output_brain 
        else:
            cmdline += " -n"

        output_mask = options.pop("output-mask", None)
        if output_mask is not None:
            output_rois["%s_bet_mask" % data_name] = output_mask
            cmdline += " -m"

        FslProcess.run(self, {
            "cmd" : "bet2", 
            "cmdline" : cmdline,
            "output-data" : output_data, 
            "output-rois" : output_rois,
        })
