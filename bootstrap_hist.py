# coding=utf-8
# Toma una curva de luz, hace un bootstrap calcula features sobre
# las muestras y hace un histograma con ellas
# -----------------------------------------------------------------------------

import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from george import kernels
import pandas as pd
import numpy as np
import george
import FATS

import lightcurves.lc_utils as lu
import graf
import bootstrap

# Ubicacion de las curvas
# 0-1           Be_lc
# 255-256       CEPH
# 457-458       EB
# 967-968       longperiod_lc
# 1697-1698     microlensing_lc
# 2862-2863     non_variables
# 12527-12528   quasar_lc
# 12645-12646   RRL

def calc_bootstrap(lc, kernel, sampling, feature_list):
    samples_devs = bootstrap.GP_bootstrap(lc, kernel, sampling=sampling)
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
    return bootstrap_values

file_dir = 'Resultados/Histogramas/ambos/'
catalog = 'MACHO'
percentage = 0.8

paths = lu.get_lightcurve_paths(catalog=catalog)
path = paths[12700]
# path = paths[967]
# path = paths[0]

lc = lu.open_lightcurve(path, catalog=catalog)
lc = lu.filter_data(lc)
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
t_obs, y_obs, err_obs, min_time, max_time = lu.prepare_lightcurve(lc)

# Preparo GP, l son 6 dias segun lo observado en otros papers
var = np.var(y_obs)
l = 6 * (max_time - min_time) / float(lc.index[-1] - lc.index[0])
kernel = var ** 2 * kernels.ExpSquaredKernel(l ** 2)
gp = george.GP(kernel, mean=np.mean(y_obs))
gp.compute(t_obs, yerr=err_obs)

# Ajusto el gaussian process a las observaciones de la curva
x = np.linspace(np.min(t_obs), np.max(t_obs), 500)
mu, cov = gp.predict(y_obs, x)
std = np.sqrt(np.diag(cov))

# Desnormalizo los valores
mu = mu * lc['mag'].std() + lc['mag'].mean() 
std = std * lc['err'].std() + lc['err'].mean()
x = x * np.std(lc.index) + np.mean(lc.index)

plt.figure()

graf.graf_GP(x, mu, std)
plt.errorbar(lc.index, lc['mag'], yerr=lc['err'], fmt=".b", ecolor='r', capsize=0)

plt.show()
plt.close()


equal_values = calc_bootstrap(lc, kernel, 'equal', feature_list)
uniform_values = calc_bootstrap(lc, kernel, 'uniform', feature_list)

equal_df = pd.DataFrame(equal_values, columns=feature_list)
uniform_df = pd.DataFrame(uniform_values, columns=feature_list)

for f_name in feature_list:
    real_value = real_values[f_name].tolist()
    equal_values = equal_df[f_name].tolist()
    uniform_values = uniform_df[f_name].tolist()
    
    fig = plt.figure(f_name)
    ax = fig.add_subplot(111)
    
    graf.graf_hist(equal_values, real_value, 'equal std=')
    graf.graf_hist(uniform_values, real_value, 'uniform std=')

    plt.axvline(x=real_value, color = 'r', label=u'Real value', linewidth=2.0)

    plt.title(f_name)

    plt.savefig(file_dir + f_name + '.png')
    plt.close()
