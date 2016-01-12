# coding=utf-8
# Toma una curva de luz, hace un bootstrap calcula features sobre
# las muestras y hace un histograma con ellas
# -----------------------------------------------------------------------------

import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from george import kernels
import george
import numpy as np
import pandas as pd
import FATS

import lightcurves.macho_utils as lu
import bootstrap
import utils



# Ubicacion de las curvas
# 0-1           Be_lc
# 255-256       CEPH
# 457-458       EB
# 967-968       longperiod_lc
# 1697-1698     microlensing_lc
# 2862-2863     non_variables
# 12527-12528   quasar_lc
# 12645-12646   RRL

def graf_hist(values, real_value):
	plt.figure()

	mean = np.mean(values)
	std = np.std(values)
	x = np.linspace(mean - 4 * std, mean + 4 * std, 100)
	plt.plot(x, mlab.normpdf(x, mean, std), 'k--')

	n, bins, patches = plt.hist(values, 60, normed=1, histtype='bar', color = 'b', alpha=0.6)
	plt.axvline(x=real_value, color = 'r', label=u'Real value')
	plt.show()
	plt.close()

percentage = 0.8

paths = lu.get_lightcurve_paths()
path = paths[967]

lc = lu.open_lightcurve(path)
lc = utils.filter_data(lc)
lc = lc.iloc[0:int(percentage * lc.index.size)]

t_obs = lc.index.tolist()
y_obs = lc['mag'].tolist()
err_obs = lc['err'].tolist()

# Calculo el valor de las features para la curva completa
feature_list = ['Amplitude', 'AndersonDarling', 'Autocor_length', 'Beyond1Std', 'Con',
         		'Eta_e', 'LinearTrend', 'MaxSlope', 'Mean', 'Meanvariance', 'MedianAbsDev',
         		'MedianBRP', 'PairSlopeTrend', 'PercentAmplitude', 'Q31', 'Rcs', 'Skew',
         		'SlottedA_length', 'SmallKurtosis', 'Std', 'StetsonK', 'StetsonK_AC']
         
fs = FATS.FeatureSpace(Data=['magnitude', 'time', 'error'],
                       featureList=feature_list, excludeList=None)

fs = fs.calculateFeature([y_obs, t_obs, err_obs])
real_values = fs.result(method='dict')

# Preparo la curva para alimentar el GP
t_obs, y_obs, err_obs, min_time, max_time = utils.prepare_lightcurve(lc)

# Preparo GP, l son 6 dias segun lo observado en otros papers
var = np.var(y_obs)
l = 6 * (max_time - min_time) / float(lc.index[-1] - lc.index[0])
kernel = var ** 2 * kernels.ExpSquaredKernel(l ** 2)

gp = george.GP(kernel, mean=np.mean(y_obs))
gp.compute(t_obs, yerr=err_obs)

# bootstrap.graf_GP(lc, kernel)

samples_devs = bootstrap.GP_bootstrap(lc, kernel)
t_obs = samples_devs[0]
samples = samples_devs[1]
bootstrap_values = []

for s in samples:
    y_obs = s[0]
    err_obs = s[1]

    fs = FATS.FeatureSpace(Data=['magnitude', 'time', 'error'],
                       featureList=feature_list, excludeList=None)

    fs = fs.calculateFeature([y_obs, t_obs, err_obs])
    bootstrap_values.append(map(lambda x: float("{0:.6f}".format(x)),
    							fs.result(method='')))

df = pd.DataFrame(bootstrap_values, columns=feature_list)

f_name = 'StetsonK_AC'
sampled_values = df[f_name].tolist()
real_value = real_values[f_name].tolist()
graf_hist(sampled_values, real_value)
