"""Exploratory April-only seed check of RF and Extra Trees; no tuning."""
import json
from pathlib import Path

import pandas as pd
from audit_inputs import benchmark_module, provenance

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'studies/S1_outage_forecasting/benchmark'
OUT = BENCH / 'results/significance_check/statistical_audit'


def main() -> None:
    """Fit original 300-tree models with seeds 42/43; scores are dimensionless."""
    bm = benchmark_module()
    rows = []
    for site in ['BG', 'KR']:
        data = bm.load(site)
        for h in [1, 6]:
            x, y = bm.features(data, h), data.outage.shift(-h)
            valid = x.notna().all(axis=1) & y.notna()
            x, y = x[valid], y[valid].astype(int)
            start = pd.Timestamp(2018, 4, 1)
            train = (x.index < start) & (x.index + pd.Timedelta(hours=h) < start)
            test = x.index.month == 4
            for seed in [42, 43]:
                for name in ['Random Forest', 'Extra Trees']:
                    model = bm.algorithms()[name].set_params(random_state=seed, n_jobs=1)
                    model.fit(x[train], y[train])
                    p = model.predict_proba(x[test])[:, 1]
                    rows.append(dict(site=site, h=h, month=4, seed=seed, algorithm=name,
                                     train_n=int(train.sum()), test_n=int(test.sum()),
                                     train_outage_share=float(y[train].mean()),
                                     test_outage_share=float(y[test].mean()), **bm.scores(y[test], p)))
            print(f'April completed: {site}, {h} h', flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / 'april_seed_scores.csv', index=False)
    pivot = result.pivot(index=['site', 'h', 'algorithm'], columns='seed', values='brier')
    winners = []
    for (site, h, seed), group in result.groupby(['site', 'h', 'seed']):
        winners.append({'site': site, 'h': int(h), 'seed': int(seed), 'lowest_brier': group.loc[group.brier.idxmin(), 'algorithm']})
    summary = {'provenance': provenance(), 'seeds': [42, 43], 'max_absolute_brier_seed_change': float((pivot[43]-pivot[42]).abs().max()),
        'descriptive_winners': winners, 'scope': 'April only; original 300 trees and leaf size 5; no tuning',
        'limitation': 'One fold and two models do not establish full-benchmark training stability.'}
    (OUT / 'april_summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
