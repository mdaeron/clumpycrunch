#! /usr/bin/env python3
'''
Carbonate clumped-isotope data processing and error propagation

This library is designed to process and standardize carbonate clumped-isotope
analyses, from low-level data out of a dual-inlet mass spectrometer to final,
“absolute” Δ47 values with fully propagated analytical error estimates.
'''

__author__ = 'Mathieu Daëron'
__contact__ = 'daeron@lsce.ipsl.fr'
__copyright__ = 'Copyright (c) 2020 Mathieu Daëron'
__license__ = 'Modified BSD License - https://opensource.org/licenses/BSD-3-Clause'
__date__ = '2020-02-08'
__version__ = '0.1'


import os
import numpy as np
from statistics import stdev
from scipy.stats import t as tstudent
from scipy.stats import levene
from numpy import linalg
from lmfit import Minimizer, Parameters, report_fit
from matplotlib import pyplot as ppl
from matplotlib import rcParams

rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = 'Helvetica'
rcParams['font.size'] = 10
rcParams['mathtext.fontset'] = 'custom'
rcParams['mathtext.rm'] = 'sans'
rcParams['mathtext.bf'] = 'sans:bold'
rcParams['mathtext.it'] = 'sans:italic'
rcParams['mathtext.cal'] = 'sans:italic'
rcParams['mathtext.default'] = 'rm'
rcParams['xtick.major.size'] = 4
rcParams['xtick.major.width'] = 1
rcParams['ytick.major.size'] = 4
rcParams['ytick.major.width'] = 1
rcParams['axes.grid'] = False
rcParams['axes.linewidth'] = 1
rcParams['grid.linewidth'] = .75
rcParams['grid.linestyle'] = '-'
rcParams['grid.alpha'] = .15
rcParams['savefig.dpi'] = 150


def correlated_sum(X,C,f = ''):
	'''
	Compute covariance-aware linear combinations
	
	Return the mean and SE of the sum of the elements of `X`, with optional
	weights corresponding to the elements of `f`, accounting for `C`,
	the covariance matrix of `X`.
	'''
	if f == '':
		f = [1 for x in X]
	return np.dot(f,X), (np.dot(f,np.dot(C,f)))**.5


def make_csv(x, hsep = ',', vsep = '\n'):
	'''
	Formats a list of lists of strings as a CSV
	
	__Parameters__
	
	+ `x`: the list of lists of strings to format
	+ `hsep`: the field separator (a comma, by default)
	+ `vsep`: the line-ending convention to use (`'\\n'` by default)
	
	__Example__
	
	```python
	x = [['a', 'b', 'c'], ['d', 'e', 'f']]
	print(make_csv(x))
	```
	
	output:
	
	```python
	a,b,c
	d,e,f
	```
	'''
	return vsep.join([hsep.join(l) for l in x])


def pf(txt):
	'''
	Modify string `txt` to follow `lmfit.Parameter()` naming rules.
	'''
	return txt.replace('-','_').replace('.','_')


def smart_type(x):
	'''
	Tries to convert string `x` to a float if it includes a decimal point, or
	to an integer if it does not. If both attempts fail, return the original
	string unchanged.
	'''
	try:
		y = float(x)
	except ValueError:
		return x
	if '.' not in x:
		return int(y)
	return y


def pretty_table(x, header = 1, hsep = '  ', vsep = '–', align = '<'):
	'''
	Reads a list of lists of strings and outputs an ascii table
	
	__Parameters__
	
	+ `x`: a list of lists of strings
	+ `header`: the number of lines to treat as header lines
	+ `hsep`: the horizontal separator between columns
	+ `vsep`: the character to use as vertical separator
	+ `align`: string of left (`<`) or right (`>`) alignment characters.
	
	__Example__
	
	```python
	x = [['A','B', 'C'], ['1', '1.9999', 'foo'], ['10', 'x', 'bar']]
	print(pretty_table(x))
	```
	
	output:

	```python
	--  ------  ---
	A        B    C
	--  ------  ---
	1   1.9999  foo
	10       x  bar
	--  ------  ---
	```
	'''
	txt = []
	widths = [np.max([len(e) for e in c]) for c in zip(*x)]
	
	if len(widths) > len(align):
		align += '>' * (len(widths)-len(align))
	sepline = hsep.join([vsep*w for w in widths])
	txt += [sepline]
	for k,l in enumerate(x):
		if k and k == header:
			txt += [sepline]
		txt += [hsep.join([f'{e:{a}{w}}' for e, w, a in zip(l, widths, align)])]
	txt += [sepline]
	txt += ['']
	return '\n'.join(txt)


def transpose_table(x):
	'''
	Transpose a list if lists
	
	__Parameters__
	
	+ `x`: a list of lists

	__Example__
	
	```python
	x = [[1, 2], [3, 4]]
	print(transpose_table(x))
	```
	
	outputs:
	
	```python
	[[1, 3], [2, 4]]
	```

	'''
	return [[e for e in c] for c in zip(*x)]


def w_avg(X, sX) :
	'''
	Compute variance-weighted average
	
	Returns the value and SE of the weighted average of the elements of `X`,
	with relative weights equal to their inverse variances (`1/sX**2`).
	
	__Parameters__
	
	+ `X`: array-like of elements to average
	+ `sX`: array-like of the corresponding SE values

	__Tip__

	If `X` and `sX` are initially arranged as a list of `(x, sx)` doublets,
	they may be rearranged using `zip()`:
	
	```python
	foo = [(0, 0.1), (1, 0.05), (2, 0.05)]
	print(w_avg(*zip(*foo)))
	
	# output:
	# (1.3333333333333333, 0.03333333333333334)
	```
	'''
	X = [ x for x in X ]
	sX = [ sx for sx in sX ]
	W = [ sx**-2 for sx in sX ]
	W = [ w/sum(W) for w in W ]
	Xavg = sum([ w*x for w,x in zip(W,X) ])
	sXavg = sum([ w**2*sx**2 for w,sx in zip(W,sX) ])**.5
	return Xavg, sXavg


class D47data(list):
	'''
	Store and process data for a large set of Δ<sub>47</sub> analyses,
	usually comprising more than one analytical session.
	'''

	### 17O CORRECTION PARAMETERS
	R13_VPDB = 0.01118  # (Chang & Li, 1990)
	'''
	Absolute (<sup>13</sup>C/<sup>12</sup>C) ratio of VPDB.
	By default equal to 0.01118 ([Chang & Li, 1990])
	
	[Chang & Li, 1990]: http://www.cnki.com.cn/Article/CJFDTotal-JXTW199004006.htm
	'''
	
	R18_VSMOW = 0.0020052  # (Baertschi, 1976)
	'''
	Absolute (<sup>18</sup>O/<sup>16</sup>C) ratio of VSMOW.
	By default equal to 0.0020052 ([Baertschi, 1976])
	
	[Baertschi, 1976]: https://doi.org/10.1016/0012-821X(76)90115-1
	'''

	lambda_17 = 0.528  # (Barkan & Luz, 2005)
	'''
	Mass-dependent exponent for triple oxygen isotopes.
	By default equal to 0.528 ([Barkan & Luz, 2005])
	
	[Barkan & Luz, 2005]: https://doi.org/10.1002/rcm.2250
	'''

	R17_VSMOW = 0.00038475  # (Assonov & Brenninkmeijer, 2003, rescaled to R13_VPDB)
	'''
	Absolute (<sup>17</sup>O/<sup>16</sup>C) ratio of VSMOW.
	By default equal to 0.00038475 ([Daëron et al., 2016])
	
	[Daëron et al., 2016]: https://dx.doi.org/10.1016/j.chemgeo.2016.08.014
	'''

	R18_VPDB = R18_VSMOW * 1.03092
	'''
	Absolute (<sup>18</sup>O/<sup>16</sup>C) ratio of VPDB.
	By definition equal to `R18_VSMOW * 1.03092`.
	'''

	R17_VPDB = R17_VSMOW * 1.03092 ** lambda_17
	'''
	Absolute (<sup>17</sup>O/<sup>16</sup>C) ratio of VPDB.
	By definition equal to `R17_VSMOW * 1.03092 ** lambda_17`.
	'''

	LEVENE_REF_SAMPLE = 'ETH-3'
	'''
	After the Δ<sub>47</sub> standardization step, each sample is tested to
	assess whether the Δ<sub>47</sub> variance within all analyses for that
	sample is significantly larger than that observed for a given reference
	sample (using [Levene's test], which yields a p-value corresponding to
	the null hypothesis that the underlying variances are equal).
	
	`LEVENE_REF_SAMPLE` (by default equal to `'ETH-3'`) specifies which
	sample should be used as a reference for this test.
	
	[Levene's test]: https://en.wikipedia.org/wiki/Levene%27s_test
	'''
	
	SAMPLE_CONSTRAINING_WG_COMPOSITION = ('ETH-3', 1.71, -1.78) # (Bernasconi et al., 2018)
	'''
	specifies the name, δ<sup>13</sup>C<sub>VPDB</sub> and δ<sup>18</sup>O<sub>VPDB</sub>
	of the carbonate standard used by `D47data.wg()` to compute the isotopic composition
	of the working gas in each session.
	
	By default equal to `('ETH-3', 1.71, -1.78)` after [Bernasconi et al. (2018)].
	
	[Bernasconi et al. (2018)]: https://doi.org/10.1029/2017GC007385
	'''
	
	ALPHA_18O_ACID_REACTION = np.exp(3.59 / (90 + 273.15) - 1.79e-3)  # (Kim et al., 2007, calcite)
	'''
	specifies the <sup>18</sup>O/<sup>16</sup>O fractionation factor generally applicable
	to acid reactions in the dataset. Currently only used by `self.wg()`.
	
	By default equal to 1.00813 (calcite reacted at 90 °C, [Kim et al., 2007]).
	
	[Kim et al., 2007]: https://dx.doi.org/10.1016/j.chemgeo.2007.08.005
	'''

	Nominal_D47 = {
		'ETH-1': 0.258,
		'ETH-2': 0.256,
		'ETH-3': 0.691,
		}	# (Bernasconi et al., 2018)
	'''
	Nominal Δ<sub>47</sub> values assigned to the anchor samples, used in particular by
	`self.normalize()` to standardize unknown samples to a carbonate Δ<sub>47</sub>
	reference frame.
	
	By default equal to `{'ETH-1': 0.258, 'ETH-2': 0.256, 'ETH-3': 0.691}` after
	[Bernasconi et al. (2018)].
	
	[Bernasconi et al. (2018)]: https://doi.org/10.1029/2017GC007385
	'''


	def __init__(self, l = [], verbose = False, msgcolor = '\033[92m'):
		'''
		_Parameters_
		
		+ `l`: a list of dictionaries, with each element including at least the keys
		`UID`, `Session`, `Sample`, `d45`, `d46`, and `d47`.
		+ `verbose`: if `True`, print out additional information when calling `D47data`
		methods.
		+ `msgcolor`: terminal color used when printing out verbose information
		(light green by default).
		
		_Returns_ a `D47data` object derived from `list`.
		'''
		self.verbose = verbose
		self.msgcolor = msgcolor
		list.__init__(self, l)
		self.Nf = None
		self.repro = {}
		self.refresh()


	def vprint(self, txt):
		'''
		Print verbose message `txt` to screen if `self.verbose == True`.
		'''
		if self.verbose:
			print(f'{self.msgcolor}[D47data]   {txt}\033[0m')


	def refresh(self):
		'''
		Update `self.sessions`, `self.samples`, `self.anchors`, and `self.unknowns`.
		'''
		self.refresh_sessions()
		self.refresh_samples()


	def refresh_sessions(self):
		'''
		Update `self.sessions` and set `scrambling_drift`, `slope_drift`, and `wg_drift`
		to `False` for all sessions.
		'''
		self.sessions = {
			s: {'data': [r for r in self if r['Session'] == s]}
			for s in sorted({r['Session'] for r in self})
			}
		for s in self.sessions:
			self.sessions[s]['scrambling_drift'] = False
			self.sessions[s]['slope_drift'] = False
			self.sessions[s]['wg_drift'] = False


	def refresh_samples(self):
		'''
		Define `self.samples`, `self.anchors`, and `self.unknowns`.
		'''
		self.samples = {
			s: {'data': [r for r in self if r['Sample'] == s]}
			for s in sorted({r['Sample'] for r in self})
			}
		self.anchors = {s: self.samples[s] for s in self.samples if s in self.Nominal_D47}
		self.unknowns = {s: self.samples[s] for s in self.samples if s not in self.Nominal_D47}


	def read(self, filename, sep = ',', session = ''):
		'''
		Read file in csv format to load data into a `D47data` object.
		
		In the csv file, spaces befor and after field separators (`','` by default)
		are optional. Each line corresponds to a single analysis.
		
		The required fields are:
		
		+ `UID`: a unique identifier
		+ `Session`: an identifier for the analytical session
		+ `Sample`: a sample identifier
		+ `d45`, `d46`, `d47`: the working-gas delta values

		Independently known oxygen-17 anomalies may be provided as `D17O` (in ‰ relative to
		VSMOW, λ = 0.528), and are otherwise assumed to be zero. Working-gas deltas `d48`
		and `d49` may also be provided, and are also set to 0 otherwise.
		
		__Parameters__
		
		+ `fileneme`: the path of the file to read
		+ `sep`: csv separator delimiting the fields
		+ `session`: set `Session` field to this string for all analyses
		'''
		with open(filename) as fid:
			self.input(fid.read(), sep = sep, session = session)


	def input(self, txt, sep = ',', session = ''):
		'''
		Read `txt` string in csv format to load analysis data into a `D47data` object.

		In the csv string, spaces befor and after field separators (`','` by default)
		are optional. Each line corresponds to a single analysis.
		
		The required fields are:
		
		+ `UID`: a unique identifier
		+ `Session`: an identifier for the analytical session
		+ `Sample`: a sample identifier
		+ `d45`, `d46`, `d47`: the working-gas delta values

		Independently known oxygen-17 anomalies may be provided as `D17O` (in ‰ relative to
		VSMOW, λ = 0.528), and are otherwise assumed to be zero. Working-gas deltas `d48`
		and `d49` may also be provided, and are also set to 0 otherwise.
		
		__Parameters__
		
		+ `txt`: the csv string to read
		+ `sep`: csv separator delimiting the fields
		+ `session`: set `Session` field to this string for all analyses
		'''
		txt = [[x.strip() for x in l.split(sep)] for l in txt.splitlines() if l.strip()]
		data = [{k: v if k in ['UID', 'Session', 'Sample'] else smart_type(v) for k,v in zip(txt[0], l)} for l in txt[1:]]

		if session = '':
			for r in data:
				r['Session'] = session

		self += data
		self.refresh()


	def wg(self, sample = '', d13C_vpdb = '', d18O_vpdb = '', a18_acid = ''):
		'''
		Compute bulk composition of the working gas for each session
		based on the average composition, within each session,
		of a given sample.
		'''

		self.vprint(f"Computing working gas composition:")

		if sample == '':
			sample = self.SAMPLE_CONSTRAINING_WG_COMPOSITION[0]
		if d13C_vpdb == '':
			d13C_vpdb = self.SAMPLE_CONSTRAINING_WG_COMPOSITION[1]
		if d18O_vpdb == '':
			d18O_vpdb = self.SAMPLE_CONSTRAINING_WG_COMPOSITION[2]
		if a18_acid == '':
			a18_acid = self.ALPHA_18O_ACID_REACTION

		R13_s = self.R13_VPDB * (1 + d13C_vpdb / 1000)
		R17_s = self.R17_VPDB * ((1 + d18O_vpdb / 1000) * a18_acid) ** self.lambda_17
		R18_s = self.R18_VPDB * (1 + d18O_vpdb / 1000) * a18_acid

		C12_s = 1 / (1 + R13_s)
		C13_s = R13_s / (1 + R13_s)
		C16_s = 1 / (1 + R17_s + R18_s)
		C17_s = R17_s / (1 + R17_s + R18_s)
		C18_s = R18_s / (1 + R17_s + R18_s)

		C626_s = C12_s * C16_s ** 2
		C627_s = 2 * C12_s * C16_s * C17_s
		C628_s = 2 * C12_s * C16_s * C18_s
		C636_s = C13_s * C16_s ** 2
		C637_s = 2 * C13_s * C16_s * C17_s
		C727_s = C12_s * C17_s ** 2

		R45_s = (C627_s + C636_s) / C626_s
		R46_s = (C628_s + C637_s + C727_s) / C626_s

		for s in self.sessions:
			db = [r for r in self.sessions[s]['data'] if r['Sample'] == sample]
			d45_s = np.mean([r['d45'] for r in db])
			d46_s = np.mean([r['d46'] for r in db])
			R45_wg = R45_s / (1 + d45_s / 1000)
			R46_wg = R46_s / (1 + d46_s / 1000)

			d13Cwg_VPDB, d18Owg_VSMOW = self.compute_bulk_deltas(R45_wg, R46_wg)

			self.vprint(f'Session {s} WG:   δ13C_VPDB = {d13Cwg_VPDB:.3f}   δ18O_VSMOW = {d18Owg_VSMOW:.3f}')

			self.sessions[s]['d13Cwg_VPDB'] = d13Cwg_VPDB
			self.sessions[s]['d18Owg_VSMOW'] = d18Owg_VSMOW
			for r in self.sessions[s]['data']:
				r['d13Cwg_VPDB'] = d13Cwg_VPDB
				r['d18Owg_VSMOW'] = d18Owg_VSMOW


	def compute_bulk_deltas(self, R45, R46, D17O = 0):
		'''
		Compute δ13C_VPDB and δ18O_VSMOW, by solving the generalized form of equation (17)
		from Brand et al. (2010), assuming that d18O_VSMOW is not too big ( 0 ± 50 ‰) and
		solving the corresponding second-order Taylor polynomial.
		(Appendix A, Daëron et al., 2016, <https://doi.org/10.1016/j.chemgeo.2016.08.014>)
		'''

		K = np.exp(D17O / 1000) * self.R17_VSMOW * self.R18_VSMOW ** -self.lambda_17

		A = -3 * K ** 2 * self.R18_VSMOW ** (2 * self.lambda_17)
		B = 2 * K * R45 * self.R18_VSMOW ** self.lambda_17
		C = 2 * self.R18_VSMOW
		D = -R46

		aa = A * self.lambda_17 * (2 * self.lambda_17 - 1) + B * self.lambda_17 * (self.lambda_17 - 1) / 2
		bb = 2 * A * self.lambda_17 + B * self.lambda_17 + C
		cc = A + B + C + D

		d18O_VSMOW = 1000 * (-bb + (bb ** 2 - 4 * aa * cc) ** .5) / (2 * aa)

		R18 = (1 + d18O_VSMOW / 1000) * self.R18_VSMOW
		R17 = K * R18 ** self.lambda_17
		R13 = R45 - 2 * R17

		d13C_VPDB = 1000 * (R13 / self.R13_VPDB - 1)

		return d13C_VPDB, d18O_VSMOW


	def crunch(self):
		'''
		Compute bulk composition and raw clumped isotope anomalies for all analyses.
		'''
		for i,r in enumerate(self):
			for k in ['D17O', 'd48', 'd49']:
				if k not in r:
					r[k] = 0.
			self.compute_bulk_and_clumping_deltas(r)
		self.vprint(f"Crunched {len(self)} analyses.")


	def compute_bulk_and_clumping_deltas(self, r):
		'''
		Compute δ13C_VPDB, δ18O_VSMOW, and raw Δ47, Δ48, Δ49 values for an analysis.
		'''

		# Compute working gas R13, R18, and isobar ratios
		R13_wg = self.R13_VPDB * (1 + r['d13Cwg_VPDB'] / 1000)
		R18_wg = self.R18_VSMOW * (1 + r['d18Owg_VSMOW'] / 1000)
		R45_wg, R46_wg, R47_wg, R48_wg, R49_wg = self.compute_isobar_ratios(R13_wg, R18_wg)

		# Compute analyte isobar ratios
		R45 = (1 + r['d45'] / 1000) * R45_wg
		R46 = (1 + r['d46'] / 1000) * R46_wg
		R47 = (1 + r['d47'] / 1000) * R47_wg
		R48 = (1 + r['d48'] / 1000) * R48_wg
		R49 = (1 + r['d49'] / 1000) * R49_wg

		r['d13C_VPDB'], r['d18O_VSMOW'] = self.compute_bulk_deltas(R45, R46, D17O = r['D17O'])
		R13 = (1 + r['d13C_VPDB'] / 1000) * self.R13_VPDB
		R18 = (1 + r['d18O_VSMOW'] / 1000) * self.R18_VSMOW

		# Compute stochastic isobar ratios of the analyte
		R45stoch, R46stoch, R47stoch, R48stoch, R49stoch = self.compute_isobar_ratios(
			R13, R18, D17O = r['D17O']
		)

		# Check that R45/R45stoch and R46/R46stoch are undistinguishable from 1,
		# and raise a warning if the corresponding anomalies exceed 0.02 ppm.
		if (R45 / R45stoch - 1) > 5e-8:
			self.vprint(f'This is unexpected: R45/R45stoch - 1 = {1e6 * (R45 / R45stoch - 1):%.3f} ppm')
		if (R46 / R46stoch - 1) > 5e-8:
			self.vprint(f'This is unexpected: R46/R46stoch - 1 = {1e6 * (R46 / R46stoch - 1):%.3f} ppm')

		# Compute raw clumped isotope anomalies
		r['D47raw'] = 1000 * (R47 / R47stoch - 1)
		r['D48raw'] = 1000 * (R48 / R48stoch - 1)
		r['D49raw'] = 1000 * (R49 / R49stoch - 1)

	def compute_isobar_ratios(self, R13, R18, D17O=0, D47=0, D48=0, D49=0):
		'''
		Compute isobar ratios for a sample with isotopic ratios R13 and R18,
		optionally accounting for non-zero values of Δ17O and clumped isotope
		anomalies, all expressed in permil.
		'''

		# Compute R17
		R17 = self.R17_VSMOW * np.exp(D17O / 1000) * (R18 / self.R18_VSMOW) ** self.lambda_17

		# Compute isotope concentrations
		C12 = (1 + R13) ** -1
		C13 = C12 * R13
		C16 = (1 + R17 + R18) ** -1
		C17 = C16 * R17
		C18 = C16 * R18

		# Compute stochastic isotopologue concentrations
		C626 = C16 * C12 * C16
		C627 = C16 * C12 * C17 * 2
		C628 = C16 * C12 * C18 * 2
		C636 = C16 * C13 * C16
		C637 = C16 * C13 * C17 * 2
		C638 = C16 * C13 * C18 * 2
		C727 = C17 * C12 * C17
		C728 = C17 * C12 * C18 * 2
		C737 = C17 * C13 * C17
		C738 = C17 * C13 * C18 * 2
		C828 = C18 * C12 * C18
		C838 = C18 * C13 * C18

		# Compute stochastic isobar ratios
		R45 = (C636 + C627) / C626
		R46 = (C628 + C637 + C727) / C626
		R47 = (C638 + C728 + C737) / C626
		R48 = (C738 + C828) / C626
		R49 = C838 / C626

		# Account for stochastic anomalies
		R47 *= 1 + D47 / 1000
		R48 *= 1 + D48 / 1000
		R49 *= 1 + D49 / 1000

		# Return isobar ratios
		return R45, R46, R47, R48, R49

	def split_samples(self, samples_to_split = 'all', grouping = 'by_uid'):
		'''
		>>> Missing docstring
		'''
		if samples_to_split == 'all':
			samples_to_split = [s for s in self.unknowns]
		gkeys = {'by_uid':'UID', 'by_session':'Session'}
		self.grouping = grouping.lower()
		if self.grouping in gkeys:
			gkey = gkeys[self.grouping]
		for r in self:
			if r['Sample'] in samples_to_split:
				r['Sample_original'] = r['Sample']
				r['Sample'] = f"{r['Sample']}__{r[gkey]}"
			elif r['Sample'] in self.unknowns:
				r['Sample_original'] = r['Sample']
		self.refresh_samples()


	def unsplit_samples(self, tables = True):
		'''
		>>> Missing docstring
		'''
		unknowns_old = sorted({s for s in self.unknowns})
		CM_old = self.normalization.covar[:,:]
		VD_old = self.normalization.params.valuesdict().copy()
		vars_old = self.normalization.var_names

		unknowns_new = sorted({r['Sample_original'] for r in self if 'Sample_original' in r})
		
		Ns = len(vars_old) - len(unknowns_old)
		vars_new = vars_old[:Ns] + [f'D47_{pf(u)}' for u in unknowns_new]
		VD_new = {k: VD_old[k] for k in vars_old[:Ns]}

		W = np.zeros((len(vars_new), len(vars_old)))
		W[:Ns,:Ns] = np.eye(Ns)
		for u in unknowns_new:
			splits = sorted({r['Sample'] for r in self if 'Sample_original' in r and r['Sample_original'] == u})
			if self.grouping == 'by_session':
				weights = [self.samples[s]['SE_D47']**-2 for s in splits]
			elif self.grouping == 'by_uid':
				weights = [1 for s in splits]
			sw = sum(weights)
			weights = [w/sw for w in weights]
			W[vars_new.index(f'D47_{pf(u)}'),[vars_old.index(f'D47_{pf(s)}') for s in splits]] = weights[:]
# 		print('\nUnsplitting weights matrix:')
# 		print('\n'.join([' '.join([f'{x:.1f}' if x else ' - ' for x in l]) for l in W]))
# 		print('---')

		CM_new = W @ CM_old @ W.T
		V = W @ np.array([[VD_old[k]] for k in vars_old])
		VD_new = {k:v[0] for k,v in zip(vars_new, V)}
		
		self.normalization.covar = CM_new
		self.normalization.params.valuesdict = lambda : VD_new
		self.normalization.var_names = vars_new

		for r in self:
			if r['Sample'] in self.unknowns:
				r['Sample_split'] = r['Sample']
				r['Sample'] = r['Sample_original']
		
		self.refresh_samples()
		self.consolidate_samples()
		self.consolidate_repro()

		if tables:
			self.table_of_analyses()
			self.table_of_samples()


	def assign_timestamps(self):
		'''
		Assign a time field `t` to each analysis.
		
		If `TimeTag` is one of the data fields, `t` is equal within a given session
		to `TimeTag` minus the mean value of `TimeTag` for that session.
		Otherwise, `TimeTag` is by default equal to the index of each analysis
		in the dataset and `t` is defined as above.
		'''
		for session in self.sessions:
			sdata = self.sessions[session]['data']
			try:
				t0 = np.mean([r['TimeTag'] for r in sdata])
				for r in sdata:
					r['t'] = r['TimeTag'] - t0
			except KeyError:
				t0 = (len(sdata)-1)/2
				for t,r in enumerate(sdata):
					r['t'] = t - t0


	def normalize(self,
		method = 'integrated_fit',
		weighted_sessions = [],
		consolidate = True,
		consolidate_tables = True,
		consolidate_plots = True,
		):
		'''
		Compute absolute Δ47 values for all replicate analyses and for sample averages.
		If `method` argument is set to `'integrated_fit'`, the normalization processes all sessions
		in a single step, assuming that all samples (anchors and unknowns alike) are
		homogeneous (i.e. that their true Δ<sub>47</sub> value does not change between sessions).
		If `method` argument is set to `'independent_sessions'`, the normalization processes each
		session independently, based only on anchors analyses.
		'''

		self.normalization_method = method
		self.assign_timestamps()

		if method == 'integrated_fit':
			if weighted_sessions:
				for session_group in weighted_sessions:
					X = D47data([r for r in self if r['Session'] in session_group], verbose = self.verbose)
					result = X.normalize(method = 'integrated_fit', weighted_sessions = [], consolidate = False)
					w = np.sqrt(result.redchi)
					self.vprint(f'Session group {session_group} MRSWD = {w:.4f}')
					for r in X:
						r['wD47raw'] *= w
			else:
				self.vprint('All weights set to 1 ppm')
				for r in self:
					r['wD47raw'] = 0.001

			params = Parameters()
			for k,session in enumerate(self.sessions):
				self.vprint(f"Session {session}: scrambling_drift is {self.sessions[session]['scrambling_drift']}.")
				self.vprint(f"Session {session}: slope_drift is {self.sessions[session]['slope_drift']}.")
				self.vprint(f"Session {session}: wg_drift is {self.sessions[session]['wg_drift']}.")
				s = pf(session)
				params.add(f'a_{s}', value = 0.9)
				params.add(f'b_{s}', value = 0.)
				params.add(f'c_{s}', value = -0.9)
				params.add(f'a2_{s}', value = 0., vary = self.sessions[session]['scrambling_drift'])
				params.add(f'b2_{s}', value = 0., vary = self.sessions[session]['slope_drift'])
				params.add(f'c2_{s}', value = 0., vary = self.sessions[session]['wg_drift'])
			for sample in self.unknowns:
				params.add(f'D47_{pf(sample)}', value=0.6)

			def residuals(p):
				R = []
				for r in self:
					session = pf(r['Session'])
					sample = pf(r['Sample'])
					if r['Sample'] in self.Nominal_D47:
						R += [ (
							r['D47raw'] - (
								p[f'a_{session}'] * self.Nominal_D47[r['Sample']]
								+ p[f'b_{session}'] * r['d47']
								+	p[f'c_{session}']
								+ r['t'] * (
									p[f'a2_{session}'] * self.Nominal_D47[r['Sample']]
									+ p[f'b2_{session}'] * r['d47']
									+	p[f'c2_{session}']
									)
								)
							) / r['wD47raw'] ]
					else:
						R += [ (
							r['D47raw'] - (
								p[f'a_{session}'] * p[f'D47_{sample}']
								+ p[f'b_{session}'] * r['d47']
								+	p[f'c_{session}']
								+ r['t'] * (
									p[f'a2_{session}'] * p[f'D47_{sample}']
									+ p[f'b2_{session}'] * r['d47']
									+	p[f'c2_{session}']
									)
								)
							) / r['wD47raw'] ]
				return R

			M = Minimizer(residuals, params)
			result = M.leastsq()
			self.Nf = result.nfree
			self.t95 = tstudent.ppf(1 - 0.05/2, self.Nf)
# 			if self.verbose:
# 				report_fit(result)

			for r in self:
				s = pf(r["Session"])
				a = result.params.valuesdict()[f'a_{s}']
				b = result.params.valuesdict()[f'b_{s}']
				c = result.params.valuesdict()[f'c_{s}']
				a2 = result.params.valuesdict()[f'a2_{s}']
				b2 = result.params.valuesdict()[f'b2_{s}']
				c2 = result.params.valuesdict()[f'c2_{s}']
				r['D47'] = (r['D47raw'] - c - b * r['d47'] - c2 * r['t'] - b2 * r['t'] * r['d47']) / (a + a2 * r['t'])

			self.normalization = result
			if consolidate:
				self.consolidate(tables = consolidate_tables, plots = consolidate_plots)
			return result

		elif method == 'independent_sessions':
			for session in self.sessions:
				self.sessions[session]['Np'] = 3
				self.vprint('')
				self.vprint(f'Standardizing session {session}.')
				sdata = self.sessions[session]['data']
				A = np.array([
					[self.Nominal_D47[r['Sample']], r['d47'], 1]
					for r in sdata if r['Sample'] in self.anchors
					])
				Y = np.array([[r['D47raw']] for r in sdata if r['Sample'] in self.anchors])
				self.sessions[session]['Na'] = Y.size
				CM = linalg.inv(A.T @ A)
				a,b,c = (CM @ A.T @ Y).T[0,:3]

				self.vprint(f'a = {a:.4f}')
				self.vprint(f'b = {b:.2e}')
				self.vprint(f'c = {c:.4f}')
				self.sessions[session]['a'] = a
				self.sessions[session]['b'] = b
				self.sessions[session]['c'] = c
				self.sessions[session]['CM'] = CM.copy()

				for r in sdata :
					r['D47'] = ( r['D47raw'] - b * r['d47'] - c ) / a
			
			Nss = len(self.sessions)
			Na = len(self)
			Ns = len(self.samples)
			Nu = len(self.unknowns)
			avgD47 = {
				sample: np.mean([r['D47'] for r in self if r['Sample'] == sample])
				for sample in self.samples
				}
			chi2 = np.sum([(r['D47'] - avgD47[r['Sample']])**2 for r in self])
			rD47 = (chi2/(Na-Nu-3*Nss))**.5
			self.repro['sigma_47'] = rD47

			for session in self.sessions:
				self.sessions[session]['CM'] *= a**2 * chi2 / (Na-Nu-3*Nss)
				self.sessions[session]['SE_a'] = self.sessions[session]['CM'][0,0]**.5
				self.sessions[session]['SE_b'] = self.sessions[session]['CM'][1,1]**.5
				self.sessions[session]['SE_c'] = self.sessions[session]['CM'][2,2]**.5
			
# 			self.Nf = np.sum([self.sessions[s]['Na'] - self.sessions[s]['Np'] for s in self.sessions])
			self.Nf = len(self) - len(self.unknowns) - np.sum([self.sessions[s]['Np'] for s in self.sessions])
			self.t95 = tstudent.ppf(1 - 0.05/2, self.Nf)

			if consolidate:
				self.consolidate(tables = consolidate_tables, plots = consolidate_plots)


	def report(self):
		'''
		Prints a report on the normalization fit.
		'''
		report_fit(self.normalization)

	def normalization_error(self, session, d47, D47):
		'''
		>>> Missing docstring
		'''
		a = self.sessions[session]['a']
		b = self.sessions[session]['b']
		c = self.sessions[session]['c']
# 		s = pf(session)
# 		i = self.normalization.var_names.index(f'a_{s}')
# 		j = self.normalization.var_names.index(f'b_{s}')
# 		k = self.normalization.var_names.index(f'c_{s}')
# 		CM = np.zeros((3,3))
# 		CM[0,0] = self.normalization.covar[i,i]
# 		CM[0,1] = self.normalization.covar[i,j]
# 		CM[0,2] = self.normalization.covar[i,k]
# 		CM[1,0] = self.normalization.covar[j,i]
# 		CM[1,1] = self.normalization.covar[j,j]
# 		CM[1,2] = self.normalization.covar[j,k]
# 		CM[2,0] = self.normalization.covar[k,i]
# 		CM[2,1] = self.normalization.covar[k,j]
# 		CM[2,2] = self.normalization.covar[k,k]
		CM = self.sessions[session]['CM']

		y, x = d47, D47
		z = a * x + b * y + c
		dxdy = -b / a
		dxdz = a ** -1
		dxda = -x / a
		dxdb = -y / a
		dxdc = -a ** -1
		V = np.array([dxda, dxdb, dxdc])
		sx = (V @ CM @ V.T) ** .5
		return sx


	def table_of_sessions(self, dir = 'results', filename = 'sessions.csv', save_to_file = True, print_out = True):
		'''
		>>> Missing docstring
		'''
		out = []
		out += [['N samples (anchors + unknowns)', f"{len(self.samples)} ({len(self.anchors)} + {len(self.unknowns)})"]]
		out += [['N analyses (anchors + unknowns)', f"{len(self)} ({len([r for r in self if r['Sample'] in self.anchors])} + {len([r for r in self if r['Sample'] in self.unknowns])})"]]
		out += [['External reproducibility of δ13C_VPDB', f"{1000 * self.repro['r_d13C_VPDB']:.1f} ppm"]]
		out += [['External reproducibility of δ18O_VSMOW', f"{1000 * self.repro['r_d18O_VSMOW']:.1f} ppm"]]
		out += [['External reproducibility of Δ47 (anchors)', f"{1000 * self.repro['r_D47a']:.1f} ppm"]]
		out += [['External reproducibility of Δ47 (unknowns)', f"{1000 * self.repro['r_D47u']:.1f} ppm"]]
		out += [['External reproducibility of Δ47 (all)', f"{1000 * self.repro['r_D47']:.1f} ppm"]]
		out += [['Degrees of freedom (Student\'s 95% t-factor)', f"{self.Nf} ({self.t95:.2f})"]]
		out += [['Standardization method', self.normalization_method]]
		out1 = out
		print(pretty_table(out1, header = 0)) 
		
		include_a2 = any([self.sessions[session]['scrambling_drift'] for session in self.sessions])
		include_b2 = any([self.sessions[session]['slope_drift'] for session in self.sessions])
		include_c2 = any([self.sessions[session]['wg_drift'] for session in self.sessions])
		out = [['Session','Na','Nu','d13Cwg_VPDB','d18Owg_VSMOW','r_d13C','r_d18O','r_D47','a ± SE','1e3 x b ± SE','c ± SE']]
		if include_a2:
			out[-1] += ['a2 ± SE']
		if include_b2:
			out[-1] += ['b2 ± SE']
		if include_c2:
			out[-1] += ['c2 ± SE']
		for session in self.sessions:
			out += [[
				session,
				f"{self.sessions[session]['Na']}",
				f"{self.sessions[session]['Nu']}",
				f"{self.sessions[session]['d13Cwg_VPDB']:.3f}",
				f"{self.sessions[session]['d18Owg_VSMOW']:.3f}",
				f"{self.sessions[session]['r_d13C_VPDB']:.4f}",
				f"{self.sessions[session]['r_d18O_VSMOW']:.4f}",
				f"{self.sessions[session]['r_D47']:.4f}",
				f"{self.sessions[session]['a']:.3f} ± {self.sessions[session]['SE_a']:.3f}",
				f"{1e3*self.sessions[session]['b']:.3f} ± {1e3*self.sessions[session]['SE_b']:.3f}",
				f"{self.sessions[session]['c']:.3f} ± {self.sessions[session]['SE_c']:.3f}",
				]]
			if include_a2:
				if self.sessions[session]['scrambling_drift']:
					out[-1] += [f"{self.sessions[session]['a2']:.1e} ± {self.sessions[session]['SE_a2']:.1e}"]
				else:
					out[-1] += ['']
			if include_b2:
				if self.sessions[session]['slope_drift']:
					out[-1] += [f"{self.sessions[session]['b2']:.1e} ± {self.sessions[session]['SE_b2']:.1e}"]
				else:
					out[-1] += ['']
			if include_c2:
				if self.sessions[session]['wg_drift']:
					out[-1] += [f"{self.sessions[session]['c2']:.1e} ± {self.sessions[session]['SE_c2']:.1e}"]
				else:
					out[-1] += ['']

		if save_to_file:
			if not os.path.exists(dir):
				os.makedirs(dir)
			with open(f'{dir}/{filename}', 'w') as fid:
				fid.write(make_csv(out))
		if print_out:
			print(pretty_table(out))
		return out1, out

	
	def table_of_analyses(self, dir = 'results', filename = 'analyses.csv', save_to_file = True, print_out = True):
		'''
		>>> Missing docstring
		'''
		out = [['UID','Session','Sample']]
		extra_fields = [f for f in [('SampleMass','.2f'),('ColdFingerPressure','.1f'),('AcidReactionYield','.3f')] if f[0] in {k for r in self for k in r}]
		for f in extra_fields:
			out[-1] += [f[0]]
		out[-1] += ['d13Cwg_VPDB','d18Owg_VSMOW','d45','d46','d47','d48','d49','d13C_VPDB','d18O_VSMOW','D47raw','D48raw','D49raw','D47']
		for r in self:
			out += [[f"{r['UID']}",f"{r['Session']}",f"{r['Sample']}"]]
			for f in extra_fields:
				out[-1] += [f"{r[f[0]]:{f[1]}}"]
			out[-1] += [
				f"{r['d13Cwg_VPDB']:.3f}",
				f"{r['d18Owg_VSMOW']:.3f}",
				f"{r['d45']:.6f}",
				f"{r['d46']:.6f}",
				f"{r['d47']:.6f}",
				f"{r['d48']:.6f}",
				f"{r['d49']:.6f}",
				f"{r['d13C_VPDB']:.6f}",
				f"{r['d18O_VSMOW']:.6f}",
				f"{r['D47raw']:.6f}",
				f"{r['D48raw']:.6f}",
				f"{r['D49raw']:.6f}",
				f"{r['D47']:.6f}"
				]
		if save_to_file:
			if not os.path.exists(dir):
				os.makedirs(dir)
			with open(f'{dir}/{filename}', 'w') as fid:
				fid.write(make_csv(out))
		if print_out:
			print(pretty_table(out))
		return out


	def table_of_samples(self, dir = 'results', filename = 'samples.csv', save_to_file = True, print_out = True):
		'''
		>>> Missing docstring
		'''
		out = [['Sample','N','d13C_VPDB','d18O_VSMOW','D47','SE','95% CL','SD','p_Levene']]
		for sample in self.anchors:
			out += [[
				f"{sample}",
				f"{self.samples[sample]['N']}",
				f"{self.samples[sample]['d13C_VPDB']:.2f}",
				f"{self.samples[sample]['d18O_VSMOW']:.2f}",
				f"{self.samples[sample]['D47']:.4f}",'','',
				f"{self.samples[sample]['SD_D47']:.4f}" if self.samples[sample]['N'] > 1 else '', ''
				]]
		for sample in self.unknowns:
			out += [[
				f"{sample}",
				f"{self.samples[sample]['N']}",
				f"{self.samples[sample]['d13C_VPDB']:.2f}",
				f"{self.samples[sample]['d18O_VSMOW']:.2f}",
				f"{self.samples[sample]['D47']:.4f}",
				f"{self.samples[sample]['SE_D47']:.4f}",
				f"± {self.samples[sample]['SE_D47']*self.t95:.4f}",
				f"{self.samples[sample]['SD_D47']:.4f}" if self.samples[sample]['N'] > 1 else '',
				f"{self.samples[sample]['p_Levene']:.3f}" if self.samples[sample]['N'] > 1 else ''
				]]
		if save_to_file:
			if not os.path.exists(dir):
				os.makedirs(dir)
			with open(f'{dir}/{filename}', 'w') as fid:
				fid.write(make_csv(out))
		if print_out:
			print(pretty_table(out))
		return out

	def plot_sessions(self, dir = 'plots', figsize = (8,8)):
		'''
		>>> Missing docstring
		'''
		if not os.path.exists(dir):
			os.makedirs(dir)
		anchor_color = 'r'
		unknown_color = 'b'

		xmin = min([r['d47'] for r in self])
		xmax = max([r['d47'] for r in self])
		xmin -= (xmax - xmin)/10
		xmax += (xmax - xmin)/11

		ymin = min([r['D47'] for r in self])
		ymax = max([r['D47'] for r in self])
		ymin -= (ymax - ymin)/10
		ymax += (ymax - ymin)/11

		repl_kw = dict(ls = 'None', marker = 'x', mfc = 'None', ms = 4, mew = .67, alpha = 1)
		avg_kw = dict(ls = '-', marker = 'None', lw = .67, alpha = .67)
		for session in self.sessions:
			fig = ppl.figure( figsize = figsize)
			for sample in self.anchors:
				db = [r for r in self.samples[sample]['data'] if r['Session'] == session]
				if len(db):
					repl_kw['mec'] = anchor_color
					X = [r['d47'] for r in db]
					Y = [r['D47'] for r in db]
					ppl.plot(X, Y, **repl_kw)
				
					avg_kw['color'] = anchor_color
					X = [min(X)-.5, max(X)+.5]
					Y = [self.samples[sample]['D47']] * 2
					ppl.plot(X, Y, **avg_kw)
				
			for sample in self.unknowns:

				db = [r for r in self.samples[sample]['data'] if r['Session'] == session]
				if len(db):
					repl_kw['mec'] = unknown_color
					X = [r['d47'] for r in db]
					Y = [r['D47'] for r in db]
					ppl.plot(X, Y, **repl_kw)

					avg_kw['color'] = unknown_color
					X = [min(X)-.19, max(X)+.19]
					Y = [self.samples[sample]['D47']] * 2
					ppl.plot(X, Y, **avg_kw)

			XI,YI = np.meshgrid(np.linspace(xmin, xmax), np.linspace(ymin, ymax))
			SI = np.array([[self.normalization_error(session, xi, yi) for xi in XI[0,:]] for yi in YI[:,0]])
			rng = np.max(SI) - np.min(SI)
			if rng <= 0.01:
				cinterval = 0.001
			elif rng <= 0.03:
				cinterval = 0.004
			elif rng <= 0.1:
				cinterval = 0.01
			elif rng <= 0.3:
				cinterval = 0.03
			else:
				cinterval = 0.1
			cval = [np.ceil(SI.min() / .001) * .001 + k * cinterval for k in range(int(np.ceil((SI.max() - SI.min()) / cinterval)))]
			cs = ppl.contour(XI, YI, SI, cval, colors = anchor_color, alpha = .5)
			ppl.clabel(cs)

			ppl.axis([xmin, xmax, ymin, ymax])
			ppl.xlabel('δ$_{47}$ (‰ WG)')
			ppl.ylabel('Δ$_{47}$ (‰)')
			ppl.grid(alpha = .15)
			ppl.title(session, weight = 'bold')
			ppl.savefig(f'{dir}/D47model_{session}.pdf')
			ppl.close(fig)


# 	def sample_D47_covar(self, sample_1, sample_2 = ''):
# 		'''
# 		Covariance between Δ47 values of samples
# 		
# 		Returns the covariance (or the variance, if sample_1 == sample_2)
# 		between the average Δ47 values of two samples. Also returns the
# 		variance if only sample_1 is specified.
# 		'''
# 		i = self.normalization.var_names.index(f'D47_{pf(sample_1)}')
# 		if sample_2 in [sample_1,'']:
# 			return self.normalization.covar[i,i]
# 		else:
# 			j = self.normalization.var_names.index(f'D47_{pf(sample_2)}')
# 			return self.normalization.covar[i,j]
# 			

	def consolidate_samples(self):
		'''
		>>> Missing docstring
		'''
		D47_ref_pop = [r['D47'] for r in self.samples[self.LEVENE_REF_SAMPLE]['data']]
		for sample in self.samples:
			self.samples[sample]['N'] = len(self.samples[sample]['data'])
			if self.samples[sample]['N'] > 1:
				self.samples[sample]['SD_D47'] = stdev([r['D47'] for r in self.samples[sample]['data']])

			self.samples[sample]['d13C_VPDB'] = np.mean([r['d13C_VPDB'] for r in self.samples[sample]['data']])
			self.samples[sample]['d18O_VSMOW'] = np.mean([r['d18O_VSMOW'] for r in self.samples[sample]['data']])

			D47_pop = [r['D47'] for r in self.samples[sample]['data']]
			if len(D47_pop) > 1:
				self.samples[sample]['p_Levene'] = levene(D47_ref_pop, D47_pop, center = 'median')[1]

		if self.normalization_method == 'integrated_fit':
			for sample in self.anchors:
				self.samples[sample]['D47'] = self.Nominal_D47[sample]
				self.samples[sample]['SE_D47'] = 0.
			for sample in self.unknowns:
				self.samples[sample]['D47'] = self.normalization.params.valuesdict()[f'D47_{pf(sample)}']
				self.samples[sample]['SE_D47'] = self.sample_D47_covar(sample)**.5

		elif self.normalization_method == 'independent_sessions':
			for sample in self.anchors:
				self.samples[sample]['D47'] = self.Nominal_D47[sample]
				self.samples[sample]['SE_D47'] = 0.
			for sample in self.unknowns:
				session_avg = []
				for session in self.sessions:
					sdata = [r for r in self.sessions[session]['data'] if r['Sample'] == sample]
					if sdata:
						avg_D47 = np.mean([r['D47'] for r in sdata])
						avg_d47 = np.mean([r['d47'] for r in sdata])
						sigma_s = self.normalization_error(session, avg_d47, avg_D47)
						sigma_u = self.repro['sigma_47'] / len(sdata)**.5
						session_avg.append((avg_D47, (sigma_u**2 + sigma_s**2)**.5))
				self.samples[sample]['D47'], self.samples[sample]['SE_D47'] = w_avg(*zip(*session_avg))


	def consolidate_sessions(self):
		'''
		>>> Missing docstring
		'''
		for session in self.sessions:
			self.sessions[session]['Na'] = len([r for r in self.sessions[session]['data'] if r['Sample'] in self.anchors])
			self.sessions[session]['Nu'] = len([r for r in self.sessions[session]['data'] if r['Sample'] in self.unknowns])

			self.sessions[session]['r_d13C_VPDB'] = self.compute_reproducibility('d13C_VPDB', samples = 'anchors', sessions = [session])
			self.sessions[session]['r_d18O_VSMOW'] = self.compute_reproducibility('d18O_VSMOW', samples = 'anchors', sessions = [session])
			self.sessions[session]['r_D47'] = self.compute_reproducibility('D47', sessions = [session])

		if self.normalization_method == 'integrated_fit':
			for session in self.sessions:

				self.sessions[session]['Np'] = 3
				for k in ['scrambling', 'slope', 'wg']:
					if self.sessions[session][f'{k}_drift']:
						self.sessions[session]['Np'] += 1

				self.sessions[session]['a'] = self.normalization.params.valuesdict()[f'a_{pf(session)}']
				i = self.normalization.var_names.index(f'a_{pf(session)}')
				self.sessions[session]['SE_a'] = self.normalization.covar[i,i]**.5

				self.sessions[session]['b'] = self.normalization.params.valuesdict()[f'b_{pf(session)}']
				i = self.normalization.var_names.index(f'b_{pf(session)}')
				self.sessions[session]['SE_b'] = self.normalization.covar[i,i]**.5

				self.sessions[session]['c'] = self.normalization.params.valuesdict()[f'c_{pf(session)}']
				i = self.normalization.var_names.index(f'c_{pf(session)}')
				self.sessions[session]['SE_c'] = self.normalization.covar[i,i]**.5

				self.sessions[session]['a2'] = self.normalization.params.valuesdict()[f'a2_{pf(session)}']
				if self.sessions[session]['scrambling_drift']:
					i = self.normalization.var_names.index(f'a2_{pf(session)}')
					self.sessions[session]['SE_a2'] = self.normalization.covar[i,i]**.5
				else:
					self.sessions[session]['SE_a2'] = 0.

				self.sessions[session]['b2'] = self.normalization.params.valuesdict()[f'b2_{pf(session)}']
				if self.sessions[session]['slope_drift']:
					i = self.normalization.var_names.index(f'b2_{pf(session)}')
					self.sessions[session]['SE_b2'] = self.normalization.covar[i,i]**.5
				else:
					self.sessions[session]['SE_b2'] = 0.

				self.sessions[session]['c2'] = self.normalization.params.valuesdict()[f'c2_{pf(session)}']
				if self.sessions[session]['wg_drift']:
					i = self.normalization.var_names.index(f'c2_{pf(session)}')
					self.sessions[session]['SE_c2'] = self.normalization.covar[i,i]**.5
				else:
					self.sessions[session]['SE_c2'] = 0.

				i = self.normalization.var_names.index(f'a_{pf(session)}')
				j = self.normalization.var_names.index(f'b_{pf(session)}')
				k = self.normalization.var_names.index(f'c_{pf(session)}')
				self.sessions[session]['CM'] = self.normalization.covar[[i,j,k],:][:,[i,j,k]]

		elif self.normalization_method == 'independent_sessions':
			pass


	def consolidate_repro(self):
		'''
		>>> Missing docstring
		'''
		self.repro['r_d13C_VPDB'] = self.compute_reproducibility('d13C_VPDB', samples = 'anchors')
		self.repro['r_d18O_VSMOW'] = self.compute_reproducibility('d18O_VSMOW', samples = 'anchors')

		N_anchor_analyses = len([r for r in self if r['Sample'] in self.anchors])

		self.repro['r_D47a'] = self.compute_reproducibility('D47', samples = 'anchors')
		self.repro['r_D47a'] /= (
			(N_anchor_analyses - np.sum([self.sessions[s]['Np'] for s in self.sessions])) / (N_anchor_analyses - len(self.anchors))
			)**.5

		self.repro['r_D47u'] = self.compute_reproducibility('D47', samples = 'unknowns')

		self.repro['r_D47'] = self.compute_reproducibility('D47', samples = 'all samples')
		self.repro['r_D47'] /= (
			(len(self) - len(self.unknowns) - np.sum([self.sessions[s]['Np'] for s in self.sessions])) / (len(self) - len(self.samples))
			)**.5


	def consolidate(self,
		tables = True,
		plots = True,
		):
		'''
		>>> Missing docstring
		'''
		self.consolidate_samples()
		self.consolidate_sessions()
		self.consolidate_repro()

		if tables:
			self.table_of_sessions()
			self.table_of_analyses()
			self.table_of_samples()
		
		if plots:
			self.plot_sessions()


	def compute_reproducibility(self, key, samples = 'all samples', sessions = 'all sessions'):
		'''
		Compute external reproducibility of `[r[key] for r in self]`.
		'''
		# NB: it's debatable whether rD47 should be computed
		# with Nf = len(self)-len(self.samples) instead of
		# Nf = len(self) - len(self.unknwons) - 3*len(self.sessions)

		if samples == 'all samples':
			mysamples = [k for k in self.samples]
		elif samples == 'anchors':
			mysamples = [k for k in self.anchors]
		elif samples == 'unknowns':
			mysamples = [k for k in self.unknowns]
		else:
			mysamples = samples

		if sessions == 'all sessions':
			sessions = [k for k in self.sessions]

		chisq, Nf = 0, 0
		for sample in mysamples :
			X = [ r[key] for r in self if r['Sample'] == sample and r['Session'] in sessions ]
			if len(X) > 1 :
				Nf += len(X) - 1
				chisq += np.sum([ (x-np.mean(X))**2 for x in X ])
		r = (chisq / Nf)**.5 if Nf > 0 else 0
		self.vprint(f'External reproducibility of r["{key}"] is {1000*r:.1f} ppm for {samples}.')
		return r

	def sample_average(self, samples, weights = 'equal', normalize = True):
		'''
		Average Δ47 value of a group of samples, accounting for covariance.
		
		Returns the (weighed, optionally) average Δ47 value and associated SE
		of a group of samples. Weights are equal by default. If normalize is
		True, weights will be rescaled so that their sum equals 1.
		
		__Examples__

		```python
		self.sample_average(['X','Y'], [1, 2])
		```

		returns the value and SE of [Δ<sub>47</sub>(X) + 2 Δ<sub>47</sub>(Y)]/3,
		where Δ<sub>47</sub>(X) and Δ<sub>47</sub>(Y) are the average Δ<sub>47</sub>
		values of samples X and Y, respectively.

		```python
		self.sample_average(['X','Y'], [1, -1], normalize = False)
		```

		returns the value and SE of the difference Δ<sub>47</sub>(X) - Δ<sub>47</sub>(Y).
		'''
		if weights == 'equal':
			weights = [1/len(samples)] * len(samples)

		if normalize:
			s = sum(weights)
			weights = [w/s for w in weights]

		try:
# 			indices = [self.normalization.var_names.index(f'D47_{pf(sample)}') for sample in samples]
# 			C = self.normalization.covar[indices,:][:,indices]
			C = array([[self.sample_D47_covar(x, y) for x in samples] for y in samples])
			X = [self.samples[sample]['D47'] for sample in samples]
			return correlated_sum(X, C, weights)
		except ValueError:
			return (0., 0.)


	def sample_D47_covar(self, sample1, sample2 = ''):
		'''
		Covariance between Δ47 values of samples
		
		Returns the covariance (or the variance, if sample_1 == sample_2)
		between the average Δ47 values of two samples. Also returns the
		variance if only sample_1 is specified.
		'''
		if sample2 == '':
			sample2 = sample1
		if self.normalization_method == 'integrated_fit':
			i = self.normalization.var_names.index(f'D47_{pf(sample1)}')
			j = self.normalization.var_names.index(f'D47_{pf(sample2)}')
			return self.normalization.covar[i, j]		
		elif self.normalization_method == 'independent_sessions':
			if sample1 == sample2:
				return self.samples[sample1]['SE_D47']**2
			else:
				c = 0
				for session in self.sessions:
					sdata1 = [r for r in self.sessions[session]['data'] if r['Sample'] == sample1]
					sdata2 = [r for r in self.sessions[session]['data'] if r['Sample'] == sample2]
					if sdata1 and sdata2:
						a = self.sessions[session]['a']
						CM = self.sessions[session]['CM']
						avg_D47_1 = np.mean([r['D47'] for r in sdata1])
						avg_d47_1 = np.mean([r['d47'] for r in sdata1])
						avg_D47_2 = np.mean([r['D47'] for r in sdata2])
						avg_d47_2 = np.mean([r['d47'] for r in sdata2])
						c += np.array([[avg_D47_1, avg_d47_1, 1]]) @ CM @ np.array([[avg_D47_2, avg_d47_2, 1]]).T / a**2
				return float(c)
