# -*- coding: utf-8 -*-
"""
Created on Tue Jun 12 17:41:47 2018

@author: hickey.221

AlchClass.py

Describes the Alch object class. An Alch instance contains a set of data,
references, and results objects from an Alchromy analysis.

TODO: Change result_list to only be a single result per alch

"""
# External packages
import os
import pandas as pd
import numpy as np
from warnings import warn
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_pdf import PdfPages
# from matplotlib.offsetbox import AnchoredText

import pickle
import datetime
# Internal scripts
from lib import alch_deconv


class Alch:
    """
    An Alchromy analysis object. Linked to a single data file. Contains objects
    for each result produced.
    """
    def __init__(self):
        # Initialize placeholders for pandas data frames
        self.data = None
        self.ref = None
        self.common_idx = None
        self.mode = None  # 'S'imple, 'R'eplicate, 'K'inetic
        self.result = None
        self.name = "test"
        # self.outputPath = outputPath
        # self.refPath = refPath
        self.normalize = False
        self.endpoints = (-np.inf, np.inf)
        self.result_list = []
        self.ready = self.readyCheck()

    def readyCheck(self):
        if self.data is not None and self.ref is not None:
            try:
                self.clean_data()
            except ValueError as e:
                warn("Couldn't clean data"+str(e))
                return False
        else:
            # warn("Do not have both data and reference loaded")
            return False
        # Passed all tests
        return True

    def clean_data(self):
        """
        Trims all data to be within the limits, and removes data points that
        don't match (odds)
        """
        if self.ref is None or self.data is None:
            warn("Don't have all df loaded to clean")
            return
        # Find the index from the ref df
        ref_idx = self.ref.index.values
        # Find the index from the data df
        data_idx = self.data.index.values
        # Find common points and save this as the new index
        self.common_idx = np.intersect1d(ref_idx, data_idx)
        # Cut anything outside our specified cutoffs
        self.common_idx = np.array([x for x in self.common_idx if self.endpoints[0] < x < self.endpoints[1]])
        # Throw error if no overlap
        if len(self.common_idx) == 0:
            warn("No overlap in indices!")
            return
        elif len(self.common_idx) < 20:
            warn("Fewer than 20 index points remaining")
        # Slim down each df by the new index
        self.data = self.data.loc[self.common_idx]
        self.ref = self.ref.loc[self.common_idx]
        print("Cleaned successfully with", len(self.common_idx), "fitting points.")

    def generate_result(self):
        """
        Given settings about a run, generate a result object
        """
        # Currently being done separately
        # self.ready = self.readyCheck()

        if not self.ready:
            warn("Not ready to run")
            return

        # Drop index columns, should already match
        expData = self.data.drop('idx', axis=1)
        refData = self.ref.drop('idx', axis=1)
        expCols = list(expData)
        refCols = list(refData)
        print("Have cols", expCols)
        if self.mode == 'S':
            pass
        elif self.mode == 'R':
            # In replicate case, make an average of all data
            expData = expData.mean(axis=1)
        else:
            print("Don't recognize mode", self.mode)
            return

        # Make a call to deconvolution algo, store the results
        coeffs, perr = alch_deconv.doFitting(refData, expData)

        # Get fit data column now that deconvolution is complete
        self.result = pd.DataFrame(self.common_idx)
        self.result.columns = ['idx']
        self.result['data'] = expData
        print(self.result['data'])
        self.result['fit'] = alch_deconv.func(refData.T, *coeffs)
        print(refCols)
        print(coeffs/sum(coeffs))

        ss_r = np.sum((self.result['data'] - self.result['fit']) ** 2)
        print(ss_r)
        print(type(self.result))
        ss_t = np.sum((self.result['data'] - np.mean(self.result['data'])) ** 2)
        print(ss_t)
        self.r2 = 1 - (ss_r / ss_t)
        print("R^2:", self.r2)

    def Reset(self):
        """
        Erases all exp and ref data
        """
        self.data = None
        self.ref = None

    def identify(self, dataPath):
        """
        Establish information about file name and location
        """
        self.dirName = os.path.dirname(dataPath)
        self.fullName = os.path.basename(dataPath)
        self.simpleName, self.ext = os.path.splitext(self.fullName)
        #if name:
            #self.nickName = name

    def load_cols(self, df, colType, filePath):
        """
        Accept a dataframe of columns of exp data
        """
        if colType == 'exp':
            self.exp = self.clean_data(df)
            self.dataCols = list(df.drop('idx', axis=1))
            self.expPath = filePath
            self.identify(self.expPath)
        elif colType == 'ref':
            self.ref = self.clean_data(df)
            self.species = list(df.drop('idx', axis=1))
            self.refPath = filePath
        else:
            warn('Unknown colType')

    def save_pdf(self, fname, fig):
        # doc = PdfPages(fname)
        # fig.savefig(doc, format='pdf')
        # doc.close()
        pass

    def plot_results(self):
        for r in self.result_list:
            fig = r.export()
            print("Exporting", r.ts.timestamp())
            # fig.figure
            # fig.canvas.draw()
            fig.show()
            # ax_list = fig.axes
            # print(ax_list)
            self.save_pdf('output/' + str(r.ts.timestamp()) + '.pdf', fig)

    def list_results(self):
        print("Results list:")
        for r in self.result_list:
            print(r.ts.timestamp())

class Result:
    """
    A result object containing fit data, run parameters, and statistics
    """
    def __init__(self, owner, ref):
        self.owner = owner  # The Alch instance we belong to
        self.mode = 'S'  # (S)imple, (R)eplicate, (K)inetic
        self.ts = datetime.datetime.now()  # Current time (use .timestamp() for epoch)
        self.ref = ref  # Reference data frame
        self.refData = self.owner.ref.drop('idx', axis=1)  # Remove nm column
        self.expData = self.owner.exp  # Grab data from owner
        self.run_deconv()
        self.do_stats()
        self.export()

    def deconv_single(self):
        pass

    def do_stats(self):
        """
        Get some summary data about the results.
        """
        ss_r = np.sum((self.expData['data'] - self.fit)**2)
        ss_t = np.sum((self.expData['data'] - np.mean(self.expData['data']))**2)
        self.r2 = 1-(ss_r/ss_t)

    def export(self):
        """
        Method for saving spreadsheet and plot data from an individual .alch
        result
        """
        # Set up figure
        fig, ax = plt.subplots(1,1)
        ax.set_title(self.ts.timestamp())
        ax.set_xlabel('Wavelength (nm)')
        ax.set_ylabel('Absorbance')

        # Plot data
        if self.mode == 'R':
            _min= self.expData.min(axis=1)
            _max = self.expData.max(axis=1)
            ax.fill_between(self.expData['nm'], _min, _max)
        ax.plot(self.expData['nm'], self.expData['data'], 'b.-', label='data')
        ax.plot(self.expData['nm'], self.fit, 'r-', label='fit')

        # Print fit data and coefficients
        tbox = r"$R^2$ fit: {:.5f}".format(self.r2)
        anchored_text = AnchoredText(tbox, loc=5,prop=dict(color='black', size=9))
        anchored_text.patch.set(boxstyle="round,pad=0.,rounding_size=0.2",alpha=0.2)
        ax.add_artist(anchored_text)
        ax.legend(loc=1) 
        #plt.close(fig)
        #print(type(fig))
        #plt.show()
        return fig
