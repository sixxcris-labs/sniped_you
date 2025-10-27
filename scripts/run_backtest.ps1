
param(
  [string]$InputPath = "data/output/refined_complete.json",
  [double]$WeightTrends = 0.25,
  [double]$WeightReddit = 0.25,
  [double]$WeightSellThrough = 0.25,
  [double]$WeightResaleAnchor = 0.25
)

Write-Host "[backtest] input=$InputPath"

$code = @'
import json
from pathlib import Path
from statistics import mean

from app.scoring.adapters import CacheLayer, EbayAdapter, GoogleTrendsAdapter, RedditAdapter, KeepaAdapter

def clip01(x):
    return max(0.0, min(1.0, float(x)))

def run(inp, w_trends, w_reddit, w_st, w_anchor):
    p = Path(inp)
    obj = json.loads(p.read_text()) if p.exists() else {"listings": []}
    listings = obj.get("listings", [])

    cache = CacheLayer()
    ebay = EbayAdapter(cache)
    trends = GoogleTrendsAdapter(cache)
    reddit = RedditAdapter(cache)

    scored = []
    for it in listings:
        kw = (it.get("brand") or "") + " " + (it.get("model") or "")
        kw = kw.strip() or "generic"

        # compute adapter features (cached, placeholder data)
        m = ebay.compute_metrics(kw)
        st = m["sell_through_rate"]
        ra = m["resale_anchor"]
        tr = trends.trend_score(kw)
        rd = reddit.mention_score(kw)

        score = (w_trends*tr + w_reddit*rd + w_st*st + w_anchor*ra)
        scored.append({"kw": kw, "score": round(score, 3), "features": {"tr": tr, "rd": rd, "st": st, "ra": ra}})

    by_cat = {}
    for s, it in zip(scored, listings):
        cat = it.get("category") or "unknown"
        by_cat.setdefault(cat, []).append(s["score"])

    summary = {k: round(mean(v), 3) for k, v in by_cat.items() if v}
    print(json.dumps({"summary": summary, "count": len(scored)}, indent=2))

run(r"{InputPath}", {WeightTrends}, {WeightReddit}, {WeightSellThrough}, {WeightResaleAnchor})
'@

$tmp = New-TemporaryFile
Set-Content -Path $tmp -Value $code -Encoding UTF8
python $tmp
Remove-Item $tmp

