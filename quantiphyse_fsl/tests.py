"""
Quantiphyse - Tests for FSL integration

Copyright (c) 2013-2020 University of Oxford

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import unittest

from quantiphyse.processes import Process
from quantiphyse.test import ProcessTest

class FlirtProcessTest(ProcessTest):
    
    def __init__(self, *args, **kwargs):
        ProcessTest.__init__(self, *args, **kwargs)
        # Flirt needs a bigger test data set or it crashes!
        self.testshape = (15, 15, 15)

    def testMoco(self):
        yaml = """  
  - Reg:
      method: flirt
      mode: moco
      data: data_4d_moving
      ref-vol: median
      output-suffix: _flirtmoco
"""
        self.run_yaml(yaml)
        self.assertEqual(self.status, Process.SUCCEEDED)
        self.assertTrue("data_4d_moving_flirtmoco" in self.ivm.data)

    def testReg(self):
        yaml = """
  - Reg:
      method: flirt
      reg: data_3d
      ref: data_3d
      output-suffix: _flirtreg
      add-reg: mask
"""
        self.run_yaml(yaml)
        self.assertEqual(self.status, Process.SUCCEEDED)
        self.assertTrue("data_3d_flirtreg" in self.ivm.data)

    def testReg4dRef(self):
        yaml = """
  - Reg:
      method: flirt
      reg: data_3d
      ref: data_4d
      ref-vol: 1
      output-suffix: _flirtreg
      add-reg: mask
"""
        self.run_yaml(yaml)
        self.assertEqual(self.status, Process.SUCCEEDED)
        self.assertTrue("data_3d_flirtreg" in self.ivm.data)

    def testReg4dReg(self):
        yaml = """
  - Reg:
      method: flirt
      reg: data_4d
      ref: data_3d
      output-suffix: _flirtreg
"""
        self.run_yaml(yaml)
        self.assertEqual(self.status, Process.SUCCEEDED)
        self.assertTrue("data_4d_flirtreg" in self.ivm.data)

    def testRegApply(self):
        yaml = """
  - Reg:
      method: flirt
      reg: data_3d
      ref: data_3d
      output-suffix: _flirtreg
      add-reg: mask
      save-transform: flirt_xfm

  - ApplyTransform:
      data: data_3d
      transform: flirt_xfm
      output-name: data_3d_flirtreg2
"""
        self.run_yaml(yaml)
        self.assertEqual(self.status, Process.SUCCEEDED)
        self.assertTrue("data_3d_flirtreg" in self.ivm.data)
        self.assertTrue("flirt_xfm" in self.ivm.extras)
        self.assertTrue("data_3d_flirtreg2" in self.ivm.data)
        # FIXME check if registered is the same as applied

class FnirtProcessTest(ProcessTest):
    """
    FNIRT registration method process tests

    FIXME 4d and moco disabled due to slowness
    FIXME test apply after reg
    """

#     def testMoco(self):
#         yaml = """  
#   - Reg:
#       method: fnirt
#       mode: moco
#       data: data_4d_moving
#       ref-vol: median
#       output-suffix: _fnirtmoco
# """
#         self.run_yaml(yaml)
#         self.assertEqual(self.status, Process.SUCCEEDED)
#         self.assertTrue("data_4d_moving_fnirtmoco" in self.ivm.data)

    def testReg(self):
        yaml = """
  - Reg:
      method: fnirt
      reg: data_3d
      ref: data_3d
      output-suffix: _fnirtreg
      save-transform: fnirt_warp
      add-reg: mask
"""
        self.run_yaml(yaml)
        self.assertEqual(self.status, Process.SUCCEEDED)
        self.assertTrue("data_3d_fnirtreg" in self.ivm.data)
        self.assertTrue("fnirt_warp" in self.ivm.data)

#    def testReg4dRef(self):
#        yaml = """
#  - Reg:
#      method: fnirt
#      reg: data_3d
#      ref: data_4d
#      ref-vol: 1
#      output-suffix: _fnirtreg
#      add-reg: mask
#"""
#        self.run_yaml(yaml)
#        self.assertEqual(self.status, Process.SUCCEEDED)
#        self.assertTrue("data_3d_fnirtreg" in self.ivm.data)
#
#     def testReg4dReg(self):
#         yaml = """
#   - Reg:
#       method: fnirt
#       reg: data_4d
#       ref: data_3d
#       output-suffix: _fnirtreg
# """
#         self.run_yaml(yaml)
#         self.assertEqual(self.status, Process.SUCCEEDED)
#         self.assertTrue("data_4d_fnirtreg" in self.ivm.data)

if __name__ == '__main__':
    unittest.main()
