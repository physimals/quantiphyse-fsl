"""
Quantiphyse - Registration method using FSL FLIRT/MCFLIRT wrappers

Copyright (c) 2013-2018 University of Oxford
"""
import six
from PySide import QtGui

from quantiphyse.data import QpData, DataGrid, NumpyData
from quantiphyse.gui.widgets import Citation
from quantiphyse.gui.options import OptionBox, ChoiceOption, NumericOption
from quantiphyse.utils import get_plugins
from quantiphyse.utils.exceptions import QpException

from .process import qpdata_to_fslimage, fslimage_to_qpdata
from .flirt_transform import FlirtTransform

CITE_TITLE = "Improved Optimisation for the Robust and Accurate Linear Registration and Motion Correction of Brain Images"
CITE_AUTHOR = "Jenkinson, M., Bannister, P., Brady, J. M. and Smith, S. M."
CITE_JOURNAL = "NeuroImage, 17(2), 825-841, 2002"

RegMethod = get_plugins("base-classes", class_name="RegMethod")[0]

class FlirtRegMethod(RegMethod):
    """
    FLIRT/MCFLIRT registration method
    """

    def __init__(self):
        RegMethod.__init__(self, "flirt", "FLIRT/MCFLIRT")
        self.options_widget = None
        self.cost_models = {"Mutual information" : "mutualinfo",
                            "Woods" : "woods",
                            "Correlation ratio" : "corratio",
                            "Normalized correlation" : "normcorr",
                            "Normalized mutual information" : "normmi",
                            "Least squares" : "leastsq"}

    @classmethod
    def apply_transform(cls, reg_data, transform, options, queue):
        """
        Apply a previously calculated transformation to a data set

        We are not actually using FSL applyxfm for this although it would be
        an alternative option for the reference space output option. Instead
        we perform a non-lossy affine transformation and then resample onto
        the reference or registration spaces as required.
        """
        log = "Performing non-lossy affine transformation\n"
        affine = transform.voxel_to_world(reg_data.grid)
        grid = DataGrid(reg_data.grid.shape, affine)
        qpdata = NumpyData(reg_data.raw(), grid=grid, name=reg_data.name)
        
        output_space = options.pop("output-space", "ref")
        if output_space == "ref":
            qpdata = qpdata.resample(transform.ref_grid, suffix="")
            log += "Resampling onto reference grid\n"
        elif output_space == "reg":
            qpdata = qpdata.resample(transform.reg_grid, suffix="")
            log += "Resampling onto reference grid\n"
            
        print(qpdata.name)
        return qpdata, log

    @classmethod
    def reg_3d(cls, reg_data, ref_data, options, queue):
        """
        Static function for performing 3D registration

        FIXME need to resolve output data space and return xform
        """
        from fsl import wrappers as fsl
        reg = qpdata_to_fslimage(reg_data)
        ref = qpdata_to_fslimage(ref_data)
        
        output_space = options.pop("output-space", "ref")
        logstream = six.StringIO()
        flirt_output = fsl.flirt(reg, ref, out=fsl.LOAD, omat=fsl.LOAD, log={"cmd" : logstream, "stdout" : logstream, "stderr" : logstream}, **options)
        transform = FlirtTransform(ref_data.grid, flirt_output["omat"])

        if output_space == "ref":
            qpdata = fslimage_to_qpdata(flirt_output["out"], reg_data.name)
        elif output_space == "reg":
            qpdata = fslimage_to_qpdata(flirt_output["out"], reg_data.name).resample(reg_data.grid, suffix="")
            qpdata.name = reg_data.name
        elif output_space == "trans":
            trans_affine = transform.voxel_to_world(reg_data.grid)
            trans_grid = DataGrid(reg_data.grid.shape, trans_affine)
            qpdata = NumpyData(reg_data.raw(), grid=trans_grid, name=reg_data.name)
            
        return qpdata, transform, logstream.getvalue()
      
    @classmethod
    def moco(cls, moco_data, ref, options, queue):
        """
        Motion correction
        
        We use MCFLIRT to implement this
        
        :param moco_data: A single 4D QpData instance containing data to motion correct.
        :param ref: Either 3D QpData containing reference data, or integer giving 
                    the volume index of ``moco_data`` to use
        :param options: Method options as dictionary
        :param queue: Queue object which method may put progress information on to. Progress 
                      should be given as a number between 0 and 1.
        
        :return Tuple of three items. 
        
                First, motion corrected data as 4D QpData in the same space as ``moco_data``
        
                Second, if options contains ``output-transform : True``, sequence of transformations
                found, one for each volume in ``reg_data``. Each is either an affine matrix transformation 
                or a sequence of 3 warp images, the same shape as ``regdata`` If ``output-transform`` 
                is not given, returns None instead.

                Third, log information from the registration as a string.
        """
        from fsl import wrappers as fsl
        if moco_data.ndim != 4:
            raise QpException("Cannot motion correct 3D data")

        reg = qpdata_to_fslimage(moco_data)

        if isinstance(ref, int):
            options["refvol"] = ref
            ref_grid = moco_data.grid
        elif isinstance(ref, QpData):
            options["reffile"] = qpdata_to_fslimage(ref)
            ref_grid = ref.grid
        else:
            raise QpException("invalid reference object type: %s" % type(ref))
            
        logstream = six.StringIO()
        result = fsl.mcflirt(reg, out=fsl.LOAD, mats=fsl.LOAD, log={"cmd" : logstream, "stdout" : logstream, "stderr" : logstream}, **options)
        print(result)
        qpdata = fslimage_to_qpdata(result["out"], moco_data.name)
        transforms = [FlirtTransform(ref_grid, result["out.mat/MAT_%04i" % vol]) for vol in range(moco_data.nvols)]
        
        return qpdata, transforms, logstream.getvalue()
  
    def interface(self):
        """
        :return: QWidget containing registration options
        """
        if self.options_widget is None:    
            self.options_widget = QtGui.QWidget()  
            vbox = QtGui.QVBoxLayout()
            self.options_widget.setLayout(vbox)

            cite = Citation(CITE_TITLE, CITE_AUTHOR, CITE_JOURNAL)
            vbox.addWidget(cite)

            self.optbox = OptionBox()
            self.optbox.add("Cost Model", ChoiceOption(self.cost_models.keys(), self.cost_models.values()), key="cost")
            self.optbox.option("cost").value = "corratio"
            #self.optbox.add("Number of search stages", ChoiceOption([1, 2, 3, 4]), key="nstages")
            #self.optbox.option("stages").value = 2
            #self.optbox.add("Final stage interpolation", ChoiceOption(["None", "Sinc", "Spline", "Nearest neighbour"], ["", "sinc_final", "spline_final", "nn_final"]), key="final")
            #self.optbox.add("Field of view (mm)", NumericOption(minval1, maxval=100, default=20), key="fov")
            self.optbox.add("Number of bins", NumericOption(intonly=True, minval=1, maxval=1000, default=256), key="bins")
            self.optbox.add("Degrees of freedom", ChoiceOption([6, 9, 12]), key="dof")
            #self.optbox.add("Scaling", NumericOption(minval=0.1, maxval=10, default=6), key="scaling")
            #self.optbox.add("Smoothing in cost function", NumericOption(minval=0.1, maxval=10, default=1), key="smoothing")
            #self.optbox.add("Scaling factor for rotation\noptimization tolerances", NumericOption(minval=0.1, maxval=10, default=1), key="rotscale")
            #self.optbox.add("Search on gradient images", BoolOption, key="grad")

            vbox.addWidget(self.optbox)
        return self.options_widget

    def options(self):
        """
        :return: Dictionary of registration options selected
        """
        self.interface()
        opts = self.optbox.values()
        for key, value in opts.items():
            self.debug("%s: %s", key, value)
        return opts
