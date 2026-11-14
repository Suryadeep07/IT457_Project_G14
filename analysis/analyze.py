import argparse
import datetime as dt
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

def load_k6(path):
    df = pd.read_csv(path, usecols=['metric_name', 'timestamp', 'metric_value'])
    df = df[df['metric_name'].isin(['http_req_duration', 'http_req_failed'])].copy()
    df['minute'] = (df['timestamp'].astype('int64') // 60) * 60
    dur = df[df['metric_name'] == 'http_req_duration'].groupby('minute')['metric_value']
    out = pd.DataFrame({
        'p50_ms': dur.quantile(0.50),
        'p95_ms': dur.quantile(0.95),
        'rps': dur.size() / 60.0,
    })
    fail = df[df['metric_name'] == 'http_req_failed'].groupby('minute')['metric_value'].mean() * 100
    out['error_pct'] = fail
    out['error_pct'] = out['error_pct'].fillna(0)
    return out.reset_index()

def load_cw(path):
    cw = pd.read_csv(path).rename(columns={'epoch': 'minute'})
    for c in cw.columns:
        cw[c] = pd.to_numeric(cw[c], errors='coerce')
    return cw

def merge(k6, cw):
    m = pd.merge(k6, cw, on='minute', how='outer').sort_values('minute')
    if m['in_service'].isna().all() and 'healthy_hosts' in m.columns:
        m['in_service'] = m['healthy_hosts']
    m['in_service'] = m['in_service'].ffill()
    m['desired'] = m['desired'].ffill()
    m['t_min'] = (m['minute'] - k6['minute'].min()) / 60.0
    return m

def summarize(name, m, price):
    k = m.dropna(subset=['rps'])
    w = m[(m['minute'] >= k['minute'].min()) & (m['minute'] <= k['minute'].max())]
    w = w.fillna(0)
    peak = k[k['rps'] >= 0.8 * k['rps'].max()]
    hours = w['in_service'].sum() / 60.0
    row = {
        'run': name,
        'peak_rps': round(k['rps'].max(), 1),
        'peak_p95_ms_median': round(peak['p95_ms'].median(), 1),
        'peak_p95_ms_max': round(peak['p95_ms'].max(), 1),
        'error_pct_overall': round((k['error_pct'] * k['rps']).sum() / k['rps'].sum(), 2),
        'max_instances': int(w['in_service'].max()),
        'instance_hours': round(hours, 2),
        'est_cost_usd': round(hours * price, 3) if price else '',
    }
    breach = w[w['cpu'] >= 50]['minute'].min()
    added = w[w['in_service'] > w['in_service'].iloc[0]]['minute'].min()
    if pd.notna(breach) and pd.notna(added):
        row['minutes_cpu50_to_new_instance'] = round((added - breach) / 60.0, 1)
    return row

def plot_timeseries(name, m, outdir):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(m['t_min'], m['p95_ms'], color='tab:red', label='p95 response time (ms)')
    ax.plot(m['t_min'], m['p50_ms'], color='tab:blue', label='median response time (ms)')
    ax.set_xlabel('Minutes since test start')
    ax.set_ylabel('Response time (ms)')
    ax2 = ax.twinx()
    ax2.step(m['t_min'], m['in_service'], where='post', color='tab:green', label='Instances in service')
    ax2.set_ylabel('Instances')
    ax2.set_ylim(0, max(5, m['in_service'].max() + 1))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper left')
    ax.set_title(f'{name}: response time and instance count over time')
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f'fig_timeseries_{name}.png'), dpi=150)
    plt.close(fig)

def plot_vs_instances(all_m, outdir):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    top = 1
    for name, m in all_m.items():
        k = m.dropna(subset=['p95_ms', 'in_service', 'rps'])
        k = k[k['rps'] >= 0.2 * k['rps'].max()]
        ax.scatter(k['in_service'], k['p95_ms'], alpha=0.5, label=f'{name} (each dot = 1 minute)')
        med = k.groupby('in_service')['p95_ms'].median()
        ax.plot(med.index, med.values, marker='o')
        max_val = k['in_service'].max()
        top = max(top, int(max_val) if pd.notna(max_val) else 0)
    ax.set_xticks(range(1, top + 1))
    ax.set_xlabel('Instances in service')
    ax.set_ylabel('p95 response time per minute (ms)')
    ax.set_title('Response time against instance count')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig_p95_vs_instances.png'), dpi=150)
    plt.close(fig)

def plot_overlay_comparison(all_m, outdir):
    if len(all_m) < 2:
        return
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    colors = {'R1': 'tab:red', 'R2': 'tab:blue', 'R3': 'tab:purple', 'R4': 'tab:orange'}
    for name, m in all_m.items():
        k = m[(m['t_min'] >= 0) & (m['t_min'] <= 22)].dropna(subset=['p95_ms'])
        ax.plot(k['t_min'], k['p95_ms'], label=f'{name} p95 Latency (ms)', color=colors.get(name, None), linewidth=2)
    ax.set_xlabel('Minutes since test start (Ramp + Peak Window)')
    ax.set_ylabel('p95 Response Time (ms)')
    if 'R2' in all_m:
        ax2 = ax.twinx()
        k2 = all_m['R2'][(all_m['R2']['t_min'] >= 0) & (all_m['R2']['t_min'] <= 22)]
        ax2.step(k2['t_min'], k2['in_service'], where='post', color='tab:green', linestyle='--', linewidth=2, label='R2 Instances in Service')
        ax2.set_ylabel('R2 Instance Count')
        ax2.set_ylim(0, max(5, int(k2['in_service'].max()) + 1))
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='upper left')
    else:
        ax.legend(loc='upper left')
    ax.set_title('Comparison: Fixed Capacity vs. Auto Scaling Response Time & Instance Count')
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, 'fig_comparison_overlay.png'), dpi=150)
    plt.close(fig)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--k6-only', metavar='K6_CSV')
    ap.add_argument('--run', nargs=3, action='append', metavar=('NAME', 'K6_CSV', 'CW_CSV'))
    ap.add_argument('--price', type=float, default=0.0, help='USD per instance-hour')
    ap.add_argument('--out', default='results')
    a = ap.parse_args()

    if a.k6_only:
        k6 = load_k6(a.k6_only)
        fmt = lambda e: dt.datetime.fromtimestamp(e, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        k6.insert(0, 'minute_utc', k6['minute'].map(fmt))
        print(k6.drop(columns=['minute']).round(1).to_string(index=False))
        print('Use for CloudWatch: --start', fmt(k6['minute'].min() - 300), '--end', fmt(k6['minute'].max() + 360))
        return

    os.makedirs(a.out, exist_ok=True)
    all_m, rows = {}, []
    for name, k6_path, cw_path in a.run:
        m = merge(load_k6(k6_path), load_cw(cw_path))
        m.to_csv(os.path.join(a.out, f'{name}_merged.csv'), index=False)
        plot_timeseries(name, m, a.out)
        rows.append(summarize(name, m, a.price))
        all_m[name] = m

    plot_vs_instances(all_m, a.out)
    plot_overlay_comparison(all_m, a.out)
    summary = pd.DataFrame(rows)
    summary.to_csv(os.path.join(a.out, 'summary.csv'), index=False)
    print(summary.to_string(index=False))

main()
