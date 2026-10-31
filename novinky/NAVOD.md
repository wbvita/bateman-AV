# Novinky pro Bateman — jak to zapnout

Tahle složka patří do veřejného repozitáře **wbvita/bateman-AV** (ne do
`sentinel`). Obsahuje:

- `novinky/vyber.py` — skript (jen standardní Python), který z RSS Lupy,
  Živě, Rootu, CzechCrunche a iROZHLASu vybere 3 větší události dne
  (o čem píše víc redakcí + velká témata, šum jako slevy a recenze vyřadí);
- `.github/workflows/novinky.yml` — GitHub Actions ho spustí každé ráno
  a výsledek `news.json` zapíše do větve `news`.

Bateman (služba) si stáhne
`https://raw.githubusercontent.com/wbvita/bateman-AV/news/news.json`
nejvýš jednou za 3 hodiny a jen když nemá dnešní vydání. Nic o uživateli
se neposílá. Vypnutí: v okně Nastavení → Novinky (UAC), nebo
`sentinel-cli svc-news-set off`.

## Jednorázové nastavení (s Claudem)

1. Nahrát obsah složky do větve `main` repozitáře `wbvita/bateman-AV`.
2. GitHub → Settings → Actions → General → Workflow permissions:
   „Read and write permissions" (workflow zapisuje do větve `news`).
3. Actions → Novinky → „Run workflow" (první běh hned, pak každé ráno).

Repozitář je veřejný, takže Actions jsou zdarma. Zkouška na počítači:
`python novinky/vyber.py --out news.json`.
