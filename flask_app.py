#! /usr/bin/env python3

# from datetime import datetime
# from random import choices
# from string import ascii_lowercase
from flask import Flask, request, render_template, Response, send_file
from D47crunch import D47data, pretty_table, make_csv, smart_type
from D47crunch import __version__ as vD47crunch
import zipfile, io, time
from pylab import *
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import base64
from werkzeug.wsgi import FileWrapper


from matplotlib import rcParams

# rcParams['backend'] = 'Agg'
# rcParams['interactive'] = False
rcParams['font.family'] = 'Helvetica'
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

__author__ = 'Mathieu Daëron'
__contact__ = 'daeron@lsce.ipsl.fr'
__copyright__ = 'Copyright (c) 2020 Mathieu Daëron'
__license__ = 'Modified BSD License - https://opensource.org/licenses/BSD-3-Clause'
__date__ = '2020-04-22'
__version__ = '0.1'

rawdata_input_str = '''UID\tSession\tSample\td45\td46\td47\td48\td49
A01\tSession1\tETH-1\t5.79502\t11.62767\t16.89351\t24.56708\t0.79486
A02\tSession1\tIAEA-C1\t6.21907\t11.49107\t17.27749\t24.58270\t1.56318
A03\tSession1\tETH-2\t-6.05868\t-4.81718\t-11.63506\t-10.32578\t0.61352
A04\tSession1\tIAEA-C2\t-3.86184\t4.94184\t0.60612\t10.52732\t0.57118
A05\tSession1\tETH-3\t5.54365\t12.05228\t17.40555\t25.96919\t0.74608
A06\tSession1\tETH-2\t-6.06706\t-4.87710\t-11.69927\t-10.64421\t1.61234
A07\tSession1\tETH-1\t5.78821\t11.55910\t16.80191\t24.56423\t1.47963
A08\tSession1\tIAEA-C2\t-3.87692\t4.86889\t0.52185\t10.40390\t1.07032
A09\tSession1\tETH-3\t5.53984\t12.01344\t17.36863\t25.77145\t0.53264
A10\tSession1\tIAEA-C1\t6.21905\t11.44785\t17.23428\t24.30975\t1.05702
A11\tSession2\tETH-1\t5.79958\t11.63130\t16.91766\t25.12232\t1.25904
A12\tSession2\tIAEA-C1\t6.22514\t11.51264\t17.33588\t24.92770\t2.54331
A13\tSession2\tETH-2\t-6.03042\t-4.74644\t-11.52551\t-10.55907\t0.04024
A14\tSession2\tIAEA-C2\t-3.83702\t4.99278\t0.67529\t10.73885\t0.70929
A15\tSession2\tETH-3\t5.53700\t12.04892\t17.42023\t26.21793\t2.16400
A16\tSession2\tETH-2\t-6.06820\t-4.84004\t-11.68630\t-10.72563\t0.04653
A17\tSession2\tETH-1\t5.78263\t11.57182\t16.83519\t25.09964\t1.26283
A18\tSession2\tIAEA-C2\t-3.85355\t4.91943\t0.58463\t10.56221\t0.71245
A19\tSession2\tETH-3\t5.52227\t12.01174\t17.36841\t26.19829\t1.03740
A20\tSession2\tIAEA-C1\t6.21937\t11.44701\t17.26426\t24.84678\t0.76866'''

rf_input_str = '''0.258\tETH-1
0.256\tETH-2
0.691\tETH-3'''

app = Flask(__name__)

default_payload = {
	'display_results': False,
	'rawdata_input_str': rawdata_input_str,
	'rawdata_input_str_fw': pretty_table([l.split('\t') for l in rawdata_input_str.splitlines()], hsep = '  '),
	'o17_R13_VPDB': 0.01118,
	'o17_R18_VSMOW': 0.0020052,
	'o17_R17_VSMOW': 0.00038475,
	'o17_lambda': 0.528,
	'wg_setting_fromsample_samplename': 'ETH-3',
	'wg_setting_fromsample_d13C': '1.71',
	'wg_setting_fromsample_d18O': '-1.78',
	'wg_setting_fromsample_acidfrac': '1.00813',
	'rf_input_str': rf_input_str,
	}

@app.route('/', methods = ['GET', 'POST'])
def main():
	if request.method == 'GET':
		return start()
	else:
		if request.form['action'] == 'Process':
			return proceed()
		elif request.form['action'] == 'Download zipped results':
			return zipresults()

def start():
	payload = default_payload.copy()
# 	payload['token'] = datetime.now().strftime('%y%m%d') + ''.join(choices(ascii_lowercase, k=5))
	return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

def proceed():
	data = D47data()

	anchors = [l.split('\t') for l in request.form['rf_input_str'].splitlines() if '\t' in l]
	data.Nominal_D47 = {l[1]: float(l[0]) for l in anchors}

	data.input(request.form['rawdata_input_str'], '\t')

	if request.form['wg_setting'] == 'wg_setting_fromsample':
		data.wg(
			sample = request.form['wg_setting_fromsample_samplename'],
			d13C_vpdb = float(request.form['wg_setting_fromsample_d13C']),
			d18O_vpdb = float(request.form['wg_setting_fromsample_d18O']),
			a18_acid = float(request.form['wg_setting_fromsample_acidfrac'])
			)
	data.crunch()

	method = {
		'stdz_method_setting_integrated_fit': 'integrated_fit',
		'stdz_method_setting_indep_sessions': 'independent_sessions',
		}[request.form['stdz_method_setting']]


	data.normalize(
		consolidate_tables = False,
		consolidate_plots = False,
		method = method)
	
	csv = 'Session,a,b,c,va,vb,vc,covab,covac,covbc,Xa,Ya,Xu,Yu'
	for session in data.sessions:
		s = data.sessions[session]
		print(s)
		Ga = [r for r in s['data'] if r['Sample'] in data.anchors]
		Gu = [r for r in s['data'] if r['Sample'] in data.unknowns]
		csv += f"\n{session},{s['a']},{s['b']},{s['c']},{s['CM'][0,0]},{s['CM'][1,1]},{s['CM'][2,2]},{s['CM'][0,1]},{s['CM'][0,2]},{s['CM'][1,2]},{';'.join([str(r['d47']) for r in Ga])},{';'.join([str(r['D47']) for r in Ga])},{';'.join([str(r['d47']) for r in Gu])},{';'.join([str(r['D47']) for r in Gu])}"

	payload = dict(request.form)
# 	return str(payload).replace(', ','\n')
	payload['display_results'] = True
	payload['csv_of_sessions'] = csv

	summary, tosessions = data.table_of_sessions(save_to_file = False, print_out = False)
	payload['summary'] = pretty_table(summary, header = 0)
	payload['summary_rows'] = len(payload['summary'].splitlines())+2
	payload['summary_cols'] = len(payload['summary'].splitlines()[0])

	payload['table_of_sessions'] = pretty_table(tosessions)
	payload['table_of_sessions_rows'] = len(payload['table_of_sessions'].splitlines())+1
	payload['table_of_sessions_cols'] = len(payload['table_of_sessions'].splitlines()[0])
	payload['table_of_sessions_csv'] = make_csv(tosessions)

	tosamples = data.table_of_samples(save_to_file = False, print_out = False)
	payload['table_of_samples'] = pretty_table(tosamples)
	payload['table_of_samples_rows'] = len(payload['table_of_samples'].splitlines())+1
	payload['table_of_samples_cols'] = len(payload['table_of_samples'].splitlines()[0])
	payload['table_of_samples_csv'] = make_csv(tosamples)

	toanalyses = data.table_of_analyses(save_to_file = False, print_out = False)
	payload['table_of_analyses'] = pretty_table(toanalyses)
	payload['table_of_analyses_rows'] = len(payload['table_of_analyses'].splitlines())+1
	payload['table_of_analyses_cols'] = len(payload['table_of_analyses'].splitlines()[0])
	payload['table_of_analyses_csv'] = make_csv(toanalyses)

	covars = "\n\nCOVARIANCE BETWEEN SAMPLE Δ47 VALUES:\n\n"
	txt = [['Sample #1', 'Sample #2', 'Covariance', 'Correlation']]
	unknowns = [k for k in data.unknowns]
	for k, s1 in enumerate(unknowns):
		for s2 in unknowns[k+1:]:
			txt += [[
				s1,
				s2,
				f"{data.sample_D47_covar(s1,s2):.4e}",
				f"{data.sample_D47_covar(s1,s2)/data.samples[s1]['SE_D47']/data.samples[s2]['SE_D47']:.6f}",
				]]
	covars += pretty_table(txt, align = '<<>>')

	payload['report'] = f"Report generated on {time.asctime()}\nClumpyCrunch v{__version__} using D47crunch v{vD47crunch}"
	payload['report'] += "\n\nOXYGEN-17 CORRECTION PARAMETERS:\n" + pretty_table([['R13_VPDB', 'R18_VSMOW', 'R17_VSMOW', 'lambda_17'], [payload['o17_R13_VPDB'], payload['o17_R18_VSMOW'], payload['o17_R17_VSMOW'], payload['o17_lambda']]], align = '<<<<')
	payload['report'] += f"\n\nSUMMARY:\n{payload['summary']}"
	payload['report'] += f"\n\nSAMPLES:\n{payload['table_of_samples']}"
	payload['report'] += f"\n\nSESSIONS:\n{payload['table_of_sessions']}"
	payload['report'] += f"\n\nANALYSES:\n{payload['table_of_analyses']}"
	payload['report'] += covars

	txt = payload['csv_of_sessions']
	txt = [[x.strip() for x in l.split(',')] for l in txt.splitlines() if l.strip()]
	sessions = [{k: smart_type(v) for k,v in zip(txt[0], l)} for l in txt[1:]]
	payload['plots'] = []
	
	for s in sessions:
		s['Xa'] = [float(x) for x in s['Xa'].split(';')]
		s['Ya'] = [float(x) for x in s['Ya'].split(';')]
		s['Xu'] = [float(x) for x in s['Xu'].split(';')]
		s['Yu'] = [float(x) for x in s['Yu'].split(';')]

	for s in sessions:
		fig = figure(figsize = (3,3))
		subplots_adjust(.2,.15,.95,.9)
		plot_session(s)
		pngImage = io.BytesIO()
		FigureCanvas(fig).print_png(pngImage)
		pngImageB64String = "data:image/png;base64,"
		pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')
		payload['plots'] += [pngImageB64String]
		close(fig)

	return(render_template('main.html', payload = payload, vD47crunch = vD47crunch))

# @app.route("/csv/<foo>/<filename>", methods = ['POST'])
# def get_file(foo, filename):
# 	payload = dict(request.form)
# 	return Response(
# 		payload[foo],
# 		mimetype='text/plain',
# 		headers={'Content-Disposition': f'attachment;filename="{filename}"'}
# 		)
def normalization_error(a, b, c, CM, d47, D47):
	V = array([-D47, -d47, -1]) /a
	return float((V @ CM @ V.T) ** .5)

def zipresults():
	payload = dict(request.form)
# 	return str(payload).replace(', ','\n')
	mem = io.BytesIO()
	with zipfile.ZipFile(mem, 'w') as zf:

		for k, filename in [
			('report', 'report.txt'),
			('table_of_sessions_csv', 'csv/sessions.csv'),
			('table_of_samples_csv', 'csv/samples.csv'),
			('table_of_analyses_csv', 'csv/analyses.csv'),
			]:
			data = zipfile.ZipInfo(f'/{filename}')
			data.date_time = time.localtime(time.time())[:6]
			data.compress_type = zipfile.ZIP_DEFLATED
			zf.writestr(data, payload[k])
		
		txt = payload['csv_of_sessions']
		txt = [[x.strip() for x in l.split(',')] for l in txt.splitlines() if l.strip()]
		sessions = [{k: smart_type(v) for k,v in zip(txt[0], l)} for l in txt[1:]]
		
		for s in sessions:
			s['Xa'] = [float(x) for x in s['Xa'].split(';')]
			s['Ya'] = [float(x) for x in s['Ya'].split(';')]
			s['Xu'] = [float(x) for x in s['Xu'].split(';')]
			s['Yu'] = [float(x) for x in s['Yu'].split(';')]

		X = [x for s in sessions for k in ['Xa', 'Xu'] for x in s[k]]
		Y = [y for s in sessions for k in ['Ya', 'Yu'] for y in s[k]]
		xmin, xmax, ymin, ymax = [min(X), max(X), min(Y), max(Y)]
		dx = xmax - xmin
		dy = ymax - ymin
		xmin -= dx/20
		xmax += dx/20
		ymin -= dy/20
		ymax += dy/20

		for s in sessions:

			fig = figure(figsize = (5,5))
			subplots_adjust(.15,.15,.9,.9)
			plot_session(s, [xmin, xmax, ymin, ymax])
			buf = io.BytesIO()
			savefig(buf, format = 'pdf')
			close(fig)

			zf.writestr(f"/sessions/{s['Session']}.pdf", buf.getvalue())

	mem.seek(0)

	response = Response(FileWrapper(mem), mimetype="application/zip", direct_passthrough=True)
	response.headers['Content-Disposition'] = 'attachment; filename=results.zip'
	return response


def plot_session(s, axislimits = []):
	kw = dict(mfc = 'None', mec = (.9,0,0), mew = .75, ms = 4)
	plot(s['Xa'], s['Ya'], 'x', **kw)

	kw['mec'] = 'k'
	plot(s['Xu'], s['Yu'], 'x', **kw)

	if axislimits:
		xmin, xmax, ymin, ymax = axislimits
	else:
		xmin, xmax, ymin, ymax = axis()
	XI,YI = meshgrid(linspace(xmin, xmax), linspace(ymin, ymax))
	CM = array([[s['va'], s['covab'], s['covac']], [s['covab'], s['vb'], s['covbc']], [s['covac'], s['covbc'], s['vc']]])
	a, b, c = s['a'], s['b'], s['c']
	SI = array([[normalization_error(a, b, c, CM, xi, yi) for xi in XI[0,:]] for yi in YI[:,0]])

	rng = SI.max() - SI.min()
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
	
	cval = [ceil(SI.min() / .001) * .001 + k * cinterval for k in range(int(ceil((SI.max() - SI.min()) / cinterval)))]
	cs = contour(XI, YI, SI, cval, colors = 'r', alpha = .5, linewidths = .75)
	clabel(cs)

	axis([xmin, xmax, ymin, ymax])
	xlabel('δ$_{47}$ (‰ WG)')
	ylabel('Δ$_{47}$ (‰)')
	title(s['Session'])
	grid(alpha = .15)
