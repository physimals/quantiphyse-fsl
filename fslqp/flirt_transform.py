"""
Quantiphyse - Class to handle FLIRT transformations

Copyright (c) 2013-2018 University of Oxford
"""
import csv

import six
import numpy as np

from quantiphyse.data.extras import Extra
from quantiphyse.utils import get_plugins

RegMethod = get_plugins("base-classes", class_name="RegMethod")[0]

class FlirtTransform(Extra):
    """
    An Extra which defines a Flirt transformation
    """

    def __init__(self, reg_grid, ref_grid, flirt_xfm):
        self.ref_grid = ref_grid
        self.flirt_xfm = flirt_xfm
        self.w2w = self.world_to_world(reg_grid)

    def __str__(self):
        """
        Bit of a hack required here. MCFLIRT matrices are tranditionally saved without
        the reference space which means they are unusable without a reference image.
        We get around this by saving the reference space commented out
        """
        stream = six.StringIO()
        writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
        
        for row in self.ref_grid.affine:
            writer.writerow(["# "] + list(row))
        for row in self.flirt_xfm:
            writer.writerow(list(row))

        return stream.getvalue()

    def voxel_to_world(self, reg_grid):
        """
        Get the effective voxel->world transformation from applying this Flirt transform
        to a specified data grid.
        """
        fslspace_src = self._get_fsl_space(reg_grid)
        fslspace_ref = self._get_fsl_space(self.ref_grid)
        return self._matmult(self.ref_grid.affine, np.linalg.inv(fslspace_ref), self.flirt_xfm, fslspace_src)
        

    def world_to_world(self, reg_grid):
        """
        Get the effective world->world transformation from applying this Flirt transform
        to a specified data grid.
        """
        return np.dot(self.voxel_to_world(reg_grid), np.linalg.inv(reg_grid.affine))

    def _get_fsl_space(self, grid):
        """
        Return the transformation from Nifti world space into 'FSL space'

        'FSL space' is a strange land where all axes are orthogonal, all distances are in mm
        and the coordinate affine always has a negative determinant. 

        This function is ported from Workbench C++ code. I preserve the comment below
        from this code:

        'don't look at me, blame analyze and flirt'
        """
        sform = grid.affine
        dimensions = grid.shape
        if len(dimensions) < 3:
            raise ValueError("NiftiHeaderIO has less than 3 dimensions, can't generate the FSL space for it")

        determinant = np.linalg.det(sform[:3, :3])
        ret = np.identity(4)
        #pixdim = header.get_zooms()
        pixdim = grid.spacing
        for dim in range(3):
            ret[dim, dim] = pixdim[dim]

        if determinant > 0:
            # yes, they really use pixdim, despite checking the SForm/QForm for flipping 
            # - ask them, not me
            ret[0, 0] = -pixdim[0]
            ret[0, 3] = (dimensions[0] - 1) * pixdim[0]
        
        conv_factor = {
            "mm" : 1,
            "m" : 1000.0,
            "um" : 0.001
        }
        ret *= conv_factor.get(grid.units, 1)
        ret[3, 3] = 1
        return ret

    def _matmult(self, *mats):
        """ Convenience function to multiply a bunch of 4x4 matrices """
        ret = np.identity(4)
        for mat in mats:
            ret = np.dot(ret, mat) 
        return ret
