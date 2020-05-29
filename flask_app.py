#! /usr/bin/env python3

# from datetime import datetime
# from random import choices
# from string import ascii_lowercase
from flask import Flask, request, render_template, Response, send_file
from flaskext.markdown import Markdown
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
__version__ = '2.1.dev2'

rawdata_input_str = '''UID\tSession\tSample\td45\td46\td47\tNominal_d13C_VPDB\tNominal_d18O_VPDB
A01\tSession01\tETH-1\t5.795017\t11.627668\t16.893512\t2.02\t-2.19
A02\tSession01\tIAEA-C1\t6.219070\t11.491072\t17.277490
A03\tSession01\tETH-2\t-6.058681\t-4.817179\t-11.635064\t-10.17\t-18.69
A04\tSession01\tIAEA-C2\t-3.861839\t4.941839\t0.606117
A05\tSession01\tETH-3\t5.543654\t12.052277\t17.405548\t1.71\t-1.78
A06\tSession01\tMERCK\t-35.929352\t-2.087501\t-39.548484
A07\tSession01\tETH-4\t-6.222218\t-5.194170\t-11.944111
A08\tSession01\tETH-2\t-6.067055\t-4.877104\t-11.699265\t-10.17\t-18.69
A09\tSession01\tMERCK\t-35.930739\t-2.080798\t-39.545632
A10\tSession01\tETH-1\t5.788207\t11.559104\t16.801908\t2.02\t-2.19
A11\tSession01\tETH-4\t-6.217508\t-5.221407\t-11.987503
A12\tSession01\tIAEA-C2\t-3.876921\t4.868892\t0.521845
A13\tSession01\tETH-3\t5.539840\t12.013444\t17.368631\t1.71\t-1.78
A14\tSession01\tIAEA-C1\t6.219046\t11.447846\t17.234280
A15\tSession01\tMERCK\t-35.932060\t-2.088659\t-39.531627
A16\tSession01\tETH-3\t5.516658\t11.978320\t17.295740\t1.71\t-1.78
A17\tSession01\tETH-4\t-6.223370\t-5.253980\t-12.025298
A18\tSession01\tETH-2\t-6.069734\t-4.868368\t-11.688559\t-10.17\t-18.69
A19\tSession01\tIAEA-C1\t6.213642\t11.465109\t17.244547
A20\tSession01\tETH-1\t5.789982\t11.535603\t16.789811\t2.02\t-2.19
A21\tSession01\tETH-4\t-6.205703\t-5.144529\t-11.909160
A22\tSession01\tIAEA-C1\t6.212646\t11.406548\t17.187214
A23\tSession01\tETH-3\t5.531413\t11.976697\t17.332700\t1.71\t-1.78
A24\tSession01\tMERCK\t-35.926347\t-2.124579\t-39.582201
A25\tSession01\tETH-1\t5.786979\t11.527864\t16.775547\t2.02\t-2.19
A26\tSession01\tIAEA-C2\t-3.866505\t4.874630\t0.525332
A27\tSession01\tETH-2\t-6.076302\t-4.922424\t-11.753283\t-10.17\t-18.69
A28\tSession01\tIAEA-C2\t-3.878438\t4.818588\t0.467595
A29\tSession01\tETH-3\t5.546458\t12.133931\t17.501646\t1.71\t-1.78
A30\tSession01\tETH-1\t5.802916\t11.642685\t16.904286\t2.02\t-2.19
A31\tSession01\tETH-2\t-6.069274\t-4.847919\t-11.677722\t-10.17\t-18.69
A32\tSession01\tETH-3\t5.523018\t12.007363\t17.362080\t1.71\t-1.78
A33\tSession01\tETH-1\t5.802333\t11.616032\t16.884255\t2.02\t-2.19
A34\tSession01\tETH-3\t5.537375\t12.000263\t17.350856\t1.71\t-1.78
A35\tSession01\tETH-2\t-6.060713\t-4.893088\t-11.728465\t-10.17\t-18.69
A36\tSession01\tETH-3\t5.532342\t11.990022\t17.342273\t1.71\t-1.78
A37\tSession01\tETH-3\t5.533622\t11.980853\t17.342245\t1.71\t-1.78
A38\tSession01\tIAEA-C2\t-3.867587\t4.893554\t0.540404
A39\tSession01\tIAEA-C1\t6.201760\t11.406628\t17.189625
A40\tSession01\tETH-1\t5.802150\t11.563414\t16.836189\t2.02\t-2.19
A41\tSession01\tETH-2\t-6.068598\t-4.897545\t-11.722343\t-10.17\t-18.69
A42\tSession01\tMERCK\t-35.928359\t-2.098440\t-39.577150
A43\tSession01\tETH-4\t-6.219175\t-5.168031\t-11.936923
A44\tSession01\tIAEA-C2\t-3.871671\t4.871517\t0.518290
B01\tSession02\tETH-1\t5.800180\t11.640916\t16.939044\t2.02\t-2.19
B02\tSession02\tETH-1\t5.799584\t11.631297\t16.917656\t2.02\t-2.19
B03\tSession02\tIAEA-C1\t6.225135\t11.512637\t17.335876
B04\tSession02\tETH-2\t-6.030415\t-4.746444\t-11.525506\t-10.17\t-18.69
B05\tSession02\tIAEA-C2\t-3.837017\t4.992780\t0.675292
B06\tSession02\tETH-3\t5.536997\t12.048918\t17.420228\t1.71\t-1.78
B07\tSession02\tMERCK\t-35.928379\t-2.105615\t-39.594573
B08\tSession02\tETH-4\t-6.218801\t-5.185168\t-11.964407
B09\tSession02\tETH-2\t-6.068197\t-4.840037\t-11.686296\t-10.17\t-18.69
B10\tSession02\tMERCK\t-35.926951\t-2.071047\t-39.546767
B11\tSession02\tETH-1\t5.782634\t11.571818\t16.835185\t2.02\t-2.19
B12\tSession02\tETH-2\t-6.070168\t-4.877700\t-11.703876\t-10.17\t-18.69
B13\tSession02\tETH-4\t-6.214873\t-5.190550\t-11.967040
B14\tSession02\tIAEA-C2\t-3.853550\t4.919425\t0.584634
B15\tSession02\tETH-3\t5.522265\t12.011737\t17.368407\t1.71\t-1.78
B16\tSession02\tIAEA-C1\t6.219374\t11.447014\t17.264258
B17\tSession02\tMERCK\t-35.927733\t-2.103033\t-39.603494
B18\tSession02\tETH-3\t5.527002\t11.984062\t17.332660\t1.71\t-1.78
B19\tSession02\tIAEA-C2\t-3.850358\t4.889230\t0.562794
B20\tSession02\tETH-4\t-6.222398\t-5.263817\t-12.033650
B21\tSession02\tETH-3\t5.525478\t11.970096\t17.340498\t1.71\t-1.78
B22\tSession02\tETH-2\t-6.070129\t-4.941487\t-11.773824\t-10.17\t-18.69
B23\tSession02\tIAEA-C1\t6.217001\t11.434152\t17.232308
B24\tSession02\tETH-1\t5.793421\t11.533191\t16.810838\t2.02\t-2.19
B25\tSession02\tETH-4\t-6.217740\t-5.198048\t-11.977179
B26\tSession02\tIAEA-C1\t6.216912\t11.425200\t17.234224
B27\tSession02\tETH-3\t5.522238\t11.932174\t17.286903\t1.71\t-1.78
B28\tSession02\tMERCK\t-35.914404\t-2.133955\t-39.614612
B29\tSession02\tETH-1\t5.784156\t11.517244\t16.786548\t2.02\t-2.19
B30\tSession02\tIAEA-C2\t-3.852750\t4.884339\t0.551587
B31\tSession02\tETH-2\t-6.068631\t-4.924103\t-11.764507\t-10.17\t-18.69
B32\tSession02\tETH-4\t-6.220238\t-5.231375\t-12.009300
B33\tSession02\tIAEA-C2\t-3.855245\t4.866571\t0.534914
B34\tSession02\tETH-1\t5.788790\t11.544306\t16.809117\t2.02\t-2.19
B35\tSession02\tMERCK\t-35.935017\t-2.173682\t-39.664046
B36\tSession02\tETH-3\t5.518320\t11.955048\t17.300668\t1.71\t-1.78
B37\tSession02\tETH-1\t5.790564\t11.521174\t16.781304\t2.02\t-2.19
B38\tSession02\tETH-4\t-6.218809\t-5.205256\t-11.979998
B39\tSession02\tIAEA-C1\t6.204774\t11.391335\t17.181310
B40\tSession02\tETH-2\t-6.076424\t-4.967973\t-11.815466\t-10.17\t-18.69
C01\tSession03\tETH-3\t5.541868\t12.129615\t17.503738\t1.71\t-1.78
C02\tSession03\tETH-3\t5.534395\t12.034601\t17.391274\t1.71\t-1.78
C03\tSession03\tETH-1\t5.797568\t11.563575\t16.857871\t2.02\t-2.19
C04\tSession03\tETH-3\t5.529415\t11.969512\t17.342673\t1.71\t-1.78
C05\tSession03\tETH-1\t5.794026\t11.526540\t16.806934\t2.02\t-2.19
C06\tSession03\tETH-3\t5.527210\t11.937462\t17.294015\t1.71\t-1.78
C07\tSession03\tIAEA-C1\t6.220521\t11.430197\t17.242458
C08\tSession03\tETH-2\t-6.064061\t-4.900852\t-11.732976\t-10.17\t-18.69
C09\tSession03\tIAEA-C2\t-3.846482\t4.889242\t0.558395
C10\tSession03\tETH-1\t5.789644\t11.520663\t16.795837\t2.02\t-2.19
C11\tSession03\tETH-4\t-6.219385\t-5.258604\t-12.036476
C12\tSession03\tMERCK\t-35.936631\t-2.161769\t-39.693775
C13\tSession03\tETH-2\t-6.076357\t-4.939912\t-11.803553\t-10.17\t-18.69
C14\tSession03\tIAEA-C2\t-3.862518\t4.850015\t0.499777
C15\tSession03\tETH-3\t5.515822\t11.928316\t17.287739\t1.71\t-1.78
C16\tSession03\tETH-4\t-6.216625\t-5.252914\t-12.033781
C17\tSession03\tETH-1\t5.792540\t11.537788\t16.801906\t2.02\t-2.19
C18\tSession03\tIAEA-C1\t6.218853\t11.447394\t17.270859
C19\tSession03\tETH-2\t-6.070107\t-4.944520\t-11.806885\t-10.17\t-18.69
C20\tSession03\tMERCK\t-35.935001\t-2.155577\t-39.675070
C21\tSession03\tETH-3\t5.542309\t12.082338\t17.471951\t1.71\t-1.78
C22\tSession03\tETH-4\t-6.209017\t-5.137393\t-11.920935
C23\tSession03\tETH-1\t5.796781\t11.621197\t16.905496\t2.02\t-2.19
C24\tSession03\tMERCK\t-35.926449\t-2.053921\t-39.576918
C25\tSession03\tETH-2\t-6.057158\t-4.797641\t-11.644824\t-10.17\t-18.69
C26\tSession03\tIAEA-C1\t6.221982\t11.501725\t17.321709
C27\tSession03\tETH-3\t5.535162\t12.023486\t17.396560\t1.71\t-1.78
C28\tSession03\tIAEA-C2\t-3.836934\t4.984196\t0.665651
C29\tSession03\tETH-3\t5.531331\t11.991300\t17.353622\t1.71\t-1.78
C30\tSession03\tIAEA-C2\t-3.844008\t4.926554\t0.601156
C31\tSession03\tETH-2\t-6.063163\t-4.907454\t-11.765065\t-10.17\t-18.69
C32\tSession03\tMERCK\t-35.941566\t-2.163022\t-39.704731
C33\tSession03\tETH-3\t5.523894\t11.992718\t17.363902\t1.71\t-1.78
C34\tSession03\tIAEA-C1\t6.220801\t11.462090\t17.282153
C35\tSession03\tETH-1\t5.794369\t11.563017\t16.845673\t2.02\t-2.19
C36\tSession03\tETH-4\t-6.221257\t-5.272969\t-12.055444
C37\tSession03\tETH-3\t5.517832\t11.957180\t17.312487\t1.71\t-1.78
C38\tSession03\tETH-2\t-6.053330\t-4.909476\t-11.740852\t-10.17\t-18.69
C39\tSession03\tIAEA-C1\t6.217139\t11.440085\t17.244787
C40\tSession03\tETH-1\t5.794091\t11.541948\t16.826158\t2.02\t-2.19
C41\tSession03\tIAEA-C2\t-3.803466\t4.894953\t0.624184
C42\tSession03\tETH-3\t5.513788\t11.933062\t17.286883\t1.71\t-1.78
C43\tSession03\tETH-1\t5.793334\t11.569668\t16.844535\t2.02\t-2.19
C44\tSession03\tETH-2\t-6.064928\t-4.935031\t-11.786336\t-10.17\t-18.69
C45\tSession03\tETH-4\t-6.216796\t-5.300373\t-12.075033
C46\tSession03\tETH-3\t5.521772\t11.933713\t17.283775\t1.71\t-1.78
C47\tSession03\tMERCK\t-35.937762\t-2.181553\t-39.739636
D01\tSession04\tETH-4\t-6.218867\t-5.242334\t-12.032129
D02\tSession04\tIAEA-C1\t6.218458\t11.435622\t17.238776
D03\tSession04\tETH-3\t5.522006\t11.946540\t17.300601\t1.71\t-1.78
D04\tSession04\tMERCK\t-35.931765\t-2.175265\t-39.716152
D05\tSession04\tETH-1\t5.786884\t11.560397\t16.823187\t2.02\t-2.19
D06\tSession04\tIAEA-C2\t-3.846071\t4.861980\t0.534465
D07\tSession04\tETH-2\t-6.072653\t-4.917987\t-11.786215\t-10.17\t-18.69
D08\tSession04\tETH-3\t5.516592\t11.923729\t17.275641\t1.71\t-1.78
D09\tSession04\tETH-1\t5.789889\t11.531354\t16.804221\t2.02\t-2.19
D10\tSession04\tIAEA-C2\t-3.845074\t4.865635\t0.546284
D11\tSession04\tETH-1\t5.795006\t11.507829\t16.772751\t2.02\t-2.19
D12\tSession04\tETH-1\t5.791371\t11.540606\t16.822704\t2.02\t-2.19
D13\tSession04\tETH-2\t-6.074029\t-4.937379\t-11.786614\t-10.17\t-18.69
D14\tSession04\tETH-4\t-6.216977\t-5.273352\t-12.057294
D15\tSession04\tIAEA-C1\t6.214304\t11.412869\t17.227005
D16\tSession04\tETH-2\t-6.071021\t-4.966406\t-11.812116\t-10.17\t-18.69
D17\tSession04\tETH-3\t5.543181\t12.065648\t17.455042\t1.71\t-1.78
D18\tSession04\tETH-1\t5.805793\t11.632212\t16.937561\t2.02\t-2.19
D19\tSession04\tIAEA-C1\t6.230425\t11.518038\t17.342943
D20\tSession04\tETH-2\t-6.049292\t-4.811109\t-11.639895\t-10.17\t-18.69
D21\tSession04\tIAEA-C2\t-3.829436\t4.967992\t0.665451
D22\tSession04\tETH-3\t5.538827\t12.064780\t17.438156\t1.71\t-1.78
D23\tSession04\tMERCK\t-35.935604\t-2.092229\t-39.632228
D24\tSession04\tETH-4\t-6.215430\t-5.166894\t-11.939419
D25\tSession04\tETH-2\t-6.068214\t-4.868420\t-11.716099\t-10.17\t-18.69
D26\tSession04\tMERCK\t-35.918898\t-2.041585\t-39.566777
D27\tSession04\tETH-1\t5.786924\t11.584138\t16.861248\t2.02\t-2.19
D28\tSession04\tETH-2\t-6.062115\t-4.820423\t-11.664703\t-10.17\t-18.69
D29\tSession04\tETH-4\t-6.210819\t-5.160997\t-11.943417
D30\tSession04\tIAEA-C2\t-3.842542\t4.937635\t0.603831
D31\tSession04\tETH-3\t5.527648\t11.985083\t17.353603\t1.71\t-1.78
D32\tSession04\tIAEA-C1\t6.221429\t11.481788\t17.284825
D33\tSession04\tMERCK\t-35.922066\t-2.113682\t-39.642962
D34\tSession04\tETH-3\t5.521955\t11.989323\t17.345179\t1.71\t-1.78
D35\tSession04\tIAEA-C2\t-3.838229\t4.937180\t0.617586
D36\tSession04\tETH-4\t-6.215638\t-5.221584\t-11.999819
D37\tSession04\tETH-2\t-6.067508\t-4.893477\t-11.754488\t-10.17\t-18.69
D38\tSession04\tIAEA-C1\t6.214580\t11.440629\t17.254051'''

app = Flask(__name__)
Markdown(app, extensions = [
	'markdown.extensions.tables',
# 	'pymdownx.magiclink',
# 	'pymdownx.betterem',
	'pymdownx.highlight',
	'pymdownx.tilde',
	'pymdownx.caret',
# 	'pymdownx.emoji',
# 	'pymdownx.tasklist',
	'pymdownx.superfences'
	])

default_payload = {
	'display_results': False,
	'error_msg': '',
	'rawdata_input_str': rawdata_input_str,
	'o17_R13_VPDB': 0.01118,
	'o17_R18_VSMOW': 0.0020052,
	'o17_R17_VSMOW': 0.00038475,
	'o17_lambda': 0.528,
	'd13C_stdz_setting': 'd13C_stdz_setting_2pt',
	'd18O_stdz_setting': 'd18O_stdz_setting_2pt',
	'wg_setting': 'wg_setting_fromsamples',
# 	'wg_setting_fromsample_samplename': 'ETH-3',
# 	'wg_setting_fromsample_d13C': 1.71,
# 	'wg_setting_fromsample_d18O': -1.78,
	'acidfrac_setting': 1.008129,
	'rf_input_str': '0.258\tETH-1\n0.256\tETH-2\n0.691\tETH-3',
	'stdz_method_setting': 'stdz_method_setting_pooled',
	}

@app.route('/faq/')
def faq():
	with open(f'{app.root_path}/faq.md') as fid:
		md = fid.read()
	return render_template('faq.html', md = md, vD47crunch = vD47crunch)
	
	
@app.route('/readme/')
def readme():
	with open(f'{app.root_path}/README.md') as fid:
		md = fid.read()
	headless_md = md[md.find('\n'):]
	return render_template('readme.html', md = headless_md, vD47crunch = vD47crunch)
	

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
	payload = dict(request.form)
	data = D47data()

	if payload['d13C_stdz_setting'] == 'd13C_stdz_setting_2pt':
		data.d13C_STANDARDIZATION_METHOD = '2pt'
	elif payload['d13C_stdz_setting'] == 'd13C_stdz_setting_1pt':
		data.d13C_STANDARDIZATION_METHOD = '1pt'
	elif payload['d13C_stdz_setting'] == 'd13C_stdz_setting_none':
		data.d13C_STANDARDIZATION_METHOD = 'none'

	if payload['d18O_stdz_setting'] == 'd18O_stdz_setting_2pt':
		data.d18O_STANDARDIZATION_METHOD = '2pt'
	elif payload['d18O_stdz_setting'] == 'd18O_stdz_setting_1pt':
		data.d18O_STANDARDIZATION_METHOD = '1pt'
	elif payload['d18O_stdz_setting'] == 'd18O_stdz_setting_none':
		data.d18O_STANDARDIZATION_METHOD = 'none'

	anchors = [l.split('\t') for l in payload['rf_input_str'].splitlines() if '\t' in l]
	data.Nominal_D47 = {l[1]: float(l[0]) for l in anchors}

	try:
		data.R13_VPDB = float(payload['o17_R13_VPDB'])
	except:
		payload['error_msg'] = 'Check the value of R13_VPDB in oxygen-17 correction settings.'
		return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
		
	try:
		data.R18_VSMOW = float(payload['o17_R18_VSMOW'])
	except:
		payload['error_msg'] = 'Check the value of R18_VSMOW in oxygen-17 correction settings.'
		return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
		
	try:
		data.R17_VSMOW = float(payload['o17_R17_VSMOW'])
	except:
		payload['error_msg'] = 'Check the value of R17_VSMOW in oxygen-17 correction settings.'
		return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

	try:
		data.lambda_17 = float(payload['o17_lambda'])
	except:
		payload['error_msg'] = 'Check the value of λ in oxygen-17 correction settings.'
		return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

	data.input(payload['rawdata_input_str'])
# 	try:
# 		data.input(payload['rawdata_input_str'], '\t')
# 	except:
# 		payload['error_msg'] = 'Raw data input failed for some reason.'
# 		return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

	for r in data:
		for k in ['UID', 'Sample', 'Session', 'd45', 'd46', 'd47']:
			if k not in r or r[k] == '':
				payload['error_msg'] = f'Analysis "{r["UID"]}" is missing field "{k}".'
				return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
		for k in ['d45', 'd46', 'd47']:
			if not isinstance(r[k], (int, float)):
				payload['error_msg'] = f'Analysis "{r["UID"]}" should have a valid number for field "{k}".'
				return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

	if payload['wg_setting'] == 'wg_setting_fromsamples':

# 		if payload['wg_setting_fromsample_samplename'] == '':
# 			payload['error_msg'] = 'Empty sample name in WG settings.'
# 			return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
# 
# 		wg_setting_fromsample_samplename = payload['wg_setting_fromsample_samplename']
# 
# 		for s in data.sessions:
# 			if wg_setting_fromsample_samplename not in [r['Sample'] for r in data.sessions[s]['data']]:
# 				payload['error_msg'] = f'Sample name from WG settings ("{wg_setting_fromsample_samplename}") not found in session "{s}".'
# 				return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
# 
# 		try:
# 			wg_setting_fromsample_d13C = float(payload['wg_setting_fromsample_d13C'])
# 		except:
# 			payload['error_msg'] = 'Check the δ13C value in WG settings.'
# 			return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
# 
# 		try:
# 			wg_setting_fromsample_d18O = float(payload['wg_setting_fromsample_d18O'])
# 		except:
# 			payload['error_msg'] = 'Check the δ18O value in WG settings.'
# 			return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

		try:
			acidfrac = float(payload['acidfrac_setting'])
		except:
			payload['error_msg'] = 'Check the acid fractionation value.'
			return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

		if acidfrac == 0:
			payload['error_msg'] = 'Acid fractionation value should be greater than zero.'
			return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

	if payload['wg_setting'] == 'wg_setting_fromsamples':

		data.Nominal_d13C_VPDB = {}
		data.Nominal_d18O_VPDB = {}
		for r in data:
			if 'Nominal_d13C_VPDB' in r:
				if r['Sample'] in data.Nominal_d13C_VPDB:
					if data.Nominal_d13C_VPDB[r['Sample']] != r['Nominal_d13C_VPDB']:
						payload['error_msg'] = f"Inconsistent <span class='field'>Nominal_d13C_VPDB</span> value for {r['Sample']} (analysis: {r['UID']})."
						return render_template('main.html', payload = payload, vD47crunch = vD47crunch)						
				else:
					data.Nominal_d13C_VPDB[r['Sample']] = r['Nominal_d13C_VPDB']
			if 'Nominal_d18O_VPDB' in r:
				if r['Sample'] in data.Nominal_d18O_VPDB:
					if data.Nominal_d18O_VPDB[r['Sample']] != r['Nominal_d18O_VPDB']:
						payload['error_msg'] = f"Inconsistent <span class='field'>Nominal_d18O_VPDB</span> value for {r['Sample']} (analysis {r['UID']})."
						return render_template('main.html', payload = payload, vD47crunch = vD47crunch)						
				else:
					data.Nominal_d18O_VPDB[r['Sample']] = r['Nominal_d18O_VPDB']

		try:
			data.wg(a18_acid = acidfrac)
		except:
			payload['error_msg'] = 'WG computation failed for some reason.'
			return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
	
	if payload['wg_setting'] == 'wg_setting_explicit':
		for r in data:
			for k in ['d13Cwg_VPDB', 'd18Owg_VSMOW']:
				if k not in r:
					payload['error_msg'] = f'Analysis "{r["UID"]}" is missing field "{k}".'
					return render_template('main.html', payload = payload, vD47crunch = vD47crunch)
					
				
	
	try:
		data.crunch()
	except:
		payload['error_msg'] = 'Crunching step failed for some reason.'
		return render_template('main.html', payload = payload, vD47crunch = vD47crunch)

	method = {
		'stdz_method_setting_pooled': 'pooled',
		'stdz_method_setting_indep_sessions': 'indep_sessions',
		}[payload['stdz_method_setting']]


	data.standardize(
		consolidate_tables = False,
		consolidate_plots = False,
		method = method)
	
	csv = 'Session,a,b,c,va,vb,vc,covab,covac,covbc,Xa,Ya,Xu,Yu'
	for session in data.sessions:
		s = data.sessions[session]
		Ga = [r for r in s['data'] if r['Sample'] in data.anchors]
		Gu = [r for r in s['data'] if r['Sample'] in data.unknowns]
		csv += f"\n{session},{s['a']},{s['b']},{s['c']},{s['CM'][0,0]},{s['CM'][1,1]},{s['CM'][2,2]},{s['CM'][0,1]},{s['CM'][0,2]},{s['CM'][1,2]},{';'.join([str(r['d47']) for r in Ga])},{';'.join([str(r['D47']) for r in Ga])},{';'.join([str(r['d47']) for r in Gu])},{';'.join([str(r['D47']) for r in Gu])}"

# 	payload['error_msg'] = 'Foo bar.'
# 	return str(payload).replace(', ','\n')
	payload['display_results'] = True
	payload['csv_of_sessions'] = csv

	summary = data.summary(save_to_file = False, print_out = False)
	tosessions = data.table_of_sessions(save_to_file = False, print_out = False)
	payload['summary'] = pretty_table(summary, header = 0)
	payload['summary_rows'] = len(payload['summary'].splitlines())+2
	payload['summary_cols'] = len(payload['summary'].splitlines()[0])

	payload['table_of_sessions'] = pretty_table(tosessions)
	payload['table_of_sessions_rows'] = len(payload['table_of_sessions'].splitlines())+1
	payload['table_of_sessions_cols'] = len(payload['table_of_sessions'].splitlines()[0])
	payload['table_of_sessions_csv'] = make_csv(tosessions)

	tosamples = data.table_of_samples(save_to_file = False, print_out = False)
	payload['table_of_samples'] = pretty_table(tosamples)
	payload['table_of_samples'] = payload['table_of_samples'][:] + 'NB: d18O_VSMOW is the composition of the analyzed CO2.'
	payload['table_of_samples_rows'] = len(payload['table_of_samples'].splitlines())
	payload['table_of_samples_cols'] = len(payload['table_of_samples'].splitlines()[0])+1
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

	if payload['wg_setting'] == 'wg_setting_fromsample':
		payload['report'] += f"\n\nWG compositions constrained by sample {wg_setting_fromsample_samplename} with:"
		payload['report'] += f"\n    δ13C_VPDB = {wg_setting_fromsample_d13C}"
		payload['report'] += f"\n    δ18O_VPDB = {wg_setting_fromsample_d18O}"
		payload['report'] += f"\n(18O/16O) AFF = {wg_setting_fromsample_acidfrac}\n"
	elif payload['wg_setting'] == 'wg_setting_explicit':
		payload['report'] += f"\n\nWG compositions specified by user.\n"
	
	payload['report'] += f"\n\nSUMMARY:\n{payload['summary']}"
	payload['report'] += f"\n\nSAMPLES:\n{payload['table_of_samples']}\n"
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
	response.headers['Content-Disposition'] = 'attachment; filename=ClumpyCrunch.zip'
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
