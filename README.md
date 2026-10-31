# Bateman Antivirus

Antivirus pro Windows 10 a 11 (64bit) zaměřený na hrozby, které běžné
antiviry snadno přehlédnou: špehovací programy, keyloggery, krádež hesel
a cookies, ransomware a programy maskované jako dokumenty
(`faktura.pdf.exe`).

## Funkce

- **Ochrana v reálném čase** — sleduje, co programy skutečně dělají
  (přístup k heslům prohlížeče, záznam kláves, hromadné šifrování souborů),
  a nebezpečný program okamžitě zmrazí.
- **Kdo mě sleduje** — přehled programů, které používají kameru, mikrofon,
  obrazovku nebo čtou klávesnici.
- **Kontrola počítače** — rychlá kontrola, kontrola celého počítače včetně
  velkých souborů a kontrola disků USB.
- **Odvirování** — náhled toho, co se odstraní; vše lze vrátit. Obsahuje
  i opravu prohlížeče, do kterého cizí program vnutil rozšíření.
- **Automatické aktualizace** — nové verze jsou digitálně podepsané;
  Bateman je ověří a nainstaluje sám (od verze 0.2.2).
- **Novinky** — tři nejvýznamnější technologické a bezpečnostní události
  dne z českých zpravodajských webů.
- **Účet** s profilovým obrázkem a odznaky; vzhled oken lze přizpůsobit.

## Soukromí

Bateman běží jen v počítači uživatele. Z internetu stahuje pouze
podepsané aktualizace a soubor Novinek z tohoto repozitáře. Dobrovolná
diagnostická data (anonymní záznamy o chybách Batemanu) se odesílají jen se
souhlasem uživatele; výchozí stav je vypnuto.

## Stažení

**[Nejnovější verze](https://github.com/wbvita/bateman-AV/releases/latest)**

- `Bateman-Antivirus-<verze>.msi` — instalátor (doporučeno). Odinstalace
  v Nastavení → Aplikace.
- `Bateman-AV-<verze>-prenosna.zip` — verze bez instalátoru; po rozbalení
  spusťte `ZAPNOUT-BATEMAN.cmd`.

Program zatím nemá certifikát pro podepisování kódu. Windows proto může
zobrazit upozornění „Systém Windows ochránil váš počítač“; pokračujte volbou
**Další informace → Přesto spustit**. Kontrolní součty SHA-256 jsou
u každého vydání v souboru `SHA256SUMS.txt`.

Bateman může běžet současně s programem Microsoft Defender.

## Stav projektu

Zkušební verze. Chyby a falešná hlášení prosím nahlaste přes
[Issues](https://github.com/wbvita/bateman-AV/issues).
