import matplotlib
matplotlib.use('Agg') 
import numpy as np
import awkward as ak
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator


SAMPLE_STYLES = {
    'Data': {'color': 'black'},
    r'Background $Z,t\bar{t},t\bar{t}+V,VVV$': {'color': "#6b59d3"},
    r'Background $ZZ^{*}$': {'color': "#ff0000"},
    r'Signal ($m_H$ = 125 GeV)': {'color': "#00cdff"},
}


def plot(all_data, samples, lumi=36.6, fraction=1.0, GeV=1.0):
    xmin = 80 * GeV
    xmax = 250 * GeV

    step_size = 2.5 * GeV
    bin_edges = np.arange(xmin, xmax + step_size, step_size)
    bin_centres = np.arange(xmin + step_size / 2, xmax + step_size / 2, step_size)

    data_x, _ = np.histogram(ak.to_numpy(all_data['Data']['mass']), bins=bin_edges)
    data_x_errors = np.sqrt(data_x)

    signal_x = ak.to_numpy(all_data[r'Signal ($m_H$ = 125 GeV)']['mass'])
    signal_weights = ak.to_numpy(all_data[r'Signal ($m_H$ = 125 GeV)'].totalWeight)
    signal_color = SAMPLE_STYLES[r'Signal ($m_H$ = 125 GeV)']['color']

    mc_x, mc_weights, mc_colors, mc_labels = [], [], [], []
    for s in samples:
        if s not in ['Data', r'Signal ($m_H$ = 125 GeV)']:
            mc_x.append(ak.to_numpy(all_data[s]['mass']))
            mc_weights.append(ak.to_numpy(all_data[s].totalWeight))
            mc_colors.append(SAMPLE_STYLES[s]['color'])
            mc_labels.append(s)


    fig, ax = plt.subplots(figsize=(12, 8))


    ax.errorbar(bin_centres, data_x, yerr=data_x_errors, fmt='ko', label='Data')


    mc_heights = ax.hist(mc_x, bins=bin_edges, weights=mc_weights,
                         stacked=True, color=mc_colors, label=mc_labels)
    mc_x_tot = mc_heights[0][-1]


    mc_x_err = np.sqrt(np.histogram(np.hstack(mc_x), bins=bin_edges,
                                    weights=np.hstack(mc_weights) ** 2)[0])


    ax.hist(signal_x, bins=bin_edges, bottom=mc_x_tot,
            weights=signal_weights, color=signal_color,
            label=r'Signal ($m_H$ = 125 GeV)')


    ax.bar(bin_centres, 2 * mc_x_err, alpha=0.5,
           bottom=mc_x_tot - mc_x_err, color='none',
           hatch="////", width=step_size, label='Stat. Unc.')


    ax.set_xlim(xmin, xmax)
    ax.set_ylim(0, np.amax(data_x) * 2.0)
    ax.set_xlabel(r'4-lepton invariant mass $\mathrm{m_{4l}}$ [GeV]', fontsize=13, x=1, ha='right')
    ax.set_ylabel(f'Events / {step_size} GeV', y=1, ha='right')
    ax.tick_params(which='both', direction='in', top=True, right=True)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())


    plt.text(0.1, 0.93, 'ATLAS Open Data', transform=ax.transAxes, fontsize=16)
    plt.text(0.1, 0.88, 'for education', transform=ax.transAxes, style='italic', fontsize=12)
    lumi_used = str(lumi * fraction)
    plt.text(0.1, 0.82, rf'$\sqrt{{s}}$=13 TeV,$\int L dt$={lumi_used} fb$^{{-1}}$',
             transform=ax.transAxes, fontsize=16)
    plt.text(0.1, 0.76, r'$H \rightarrow ZZ^* \rightarrow 4\ell$', transform=ax.transAxes, fontsize=16)

    ax.legend(frameon=False, fontsize=16)


    plt.savefig('/app/plot.png', dpi=150, bbox_inches='tight')
    print("Plot saved as /app/plot.png")