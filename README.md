# Local Ai Generator

Samostatné Python studio pro **lokální obrázky, krátká videa a zvuky**. Nové tmavé rozhraní s fialovým akcentem, oddělené AI procesy a žádné placené generovací API.

**Verze 0.1.0 — první vývojové vydání.** Aplikace není zárukou fungování každého modelu na každém počítači. Podpora zařízení znamená dostupný backend a CPU fallback; potřebná RAM, ovladače a rychlost se liší. Produkční kvalitu a kompatibilitu je nutné ověřit na cílových strojích.

![Rozhraní](preview.png)

## První spuštění

Potřebujete **64bit Python 3.10–3.12**, moderní Windows, macOS nebo Linux. Internet je potřeba pro první instalaci knihoven a stažení modelů. Váhy nejsou součástí balíčku.

### Windows

1. Rozbalte celý projekt. Při instalaci Pythonu zaškrtněte **Add Python to PATH**.
2. Spusťte `Start.bat`. Vytvoří `.venv`, nainstaluje rozhraní a otevře aplikaci.
3. Pro univerzální CPU základ spusťte `Setup-AI-CPU.bat`. Pro GPU můžete použít `Setup-AI-GPU.bat`; instalační skript použije standardní PyPI sestavení PyTorch, jehož GPU podpora závisí na platformě a dostupném wheelu. Není to univerzální instalátor všech GPU.
4. Otevřete aplikaci, vyberte model, přečtěte jeho kartu a klikněte na **Stáhnout model**.
5. Po dokončení zadejte prompt a stiskněte **Vytvořit**. Generování se obejde bez internetu.

### macOS

`python3 start.py` otevře rozhraní. `python3 setup_ai.py --backend cpu` nainstaluje AI engine; na Macu používá standardní sestavení PyTorch s MPS na podporovaných Apple Silicon počítačích. Lze použít také `Start.command` a `Setup-AI.command` (případně nejprve `chmod +x *.command`). Intel Mac používá CPU, pokud pro danou kombinaci Pythonu a systému existuje podporované sestavení PyTorch.

### Linux

```bash
python3 start.py
python3 setup_ai.py --backend cpu
python3 start.py
```

Qt může vyžadovat systémové knihovny X11/Wayland. CPU je výchozí instalační cesta. Pro NVIDIA, AMD ROCm nebo Intel XPU nejprve nainstalujte vhodné sestavení PyTorch podle [oficiálního instalátoru](https://pytorch.org/get-started/locally/) **do projektového `.venv`**, pak spusťte:

```bash
python3 setup_ai.py --backend existing
```

Pro Windows je Python v `.venv\Scripts\python.exe`, pro macOS/Linux v `.venv/bin/python`. Instalace CPU i GPU knihoven může zabrat několik GB. Přenos celého `.venv` mezi různými OS není podporovaný.

## Co umí

- Obrázky přes SD 1.5, SDXL Base a SDXL Turbo → PNG.
- Krátké video z textu přes LTX Video → MP4. Zvukovou stopu video negeneruje.
- Zvuky a krátké hudební textury přes AudioLDM 2 → WAV, 16 kHz. Není to plnohodnotný generátor hotových písní ani samostatný dabingový engine.
- Auto / CPU / CUDA či ROCm / Apple MPS / Intel XPU podle použitého PyTorch.
- CUDA model CPU offload a VAE slicing/tiling, kde je pipeline podporuje.
- Výběr kompletní lokální Diffusers složky odpovídající vybranému typu modelu. Libovolné jiné architektury, GGUF, LoRA a samotné checkpointy tato verze nepodporuje.
- Seed, negativní prompt, kroky, guidance, rozlišení, snímky/FPS nebo délka zvuku.
- Průběh operace, chyby, ukončení pracovního procesu a náhled obrázku.
- Každý výsledek má samostatnou unikátní složku a JSON s parametry. Předchozí výstupy se nepřepisují.

Převzaty jsou jen obecné principy workflow známé z MicrostockForge, například Auto/GPU/CPU a lokální načítání modelů. Implementace je nová; soukromý zdrojový kód MicrostockForge není zkopírovaný.

## Přejmenování

Program se nově jmenuje **Local Ai Generator**, Python balíček `localaigenerator` a repozitář `local-ai-generator`. Pokud již existují data předchozí verze Local Ai Generator, aplikace použije původní adresář a rozpozná staré značky dokončeného stažení. Modely není nutné stahovat znovu. Podporuje také původní proměnnou `LOCALAIGENERATOR_HOME`.

## Modely a hardware

| Model | Použití | Praktické očekávání |
|---|---|---|
| SD 1.5 | Obrázky 512 px, menší model | Začněte zde na méně výkonných počítačích. CPU je pomalé. |
| SDXL Base | Detailnější obrázky kolem 1024 px | Vyšší nároky na RAM/VRAM, CUDA offload může pomoci. |
| SDXL Turbo | Rychlé náhledy | 1–4 kroky, guidance 0, výchozí 512 px. |
| LTX Video | Krátké tiché klipy | GPU doporučené; video na CPU může trvat velmi dlouho. |
| AudioLDM 2 | Zvuky / hudební textury | 1–10 s, nekomerční model. |

Přesné nároky nejsou zaručené. Závisí na modelu, rozlišení, délce, přesnosti vah a OS. Slabý počítač může selhat i v CPU režimu kvůli RAM. Při nedostatku paměti snižte rozlišení či počet snímků, zavřete další aplikace nebo zvolte menší model. MPS používá konzervativně float32, takže může spotřebovat více paměti. XPU a ROCm jsou dostupné pouze s odpovídajícím PyTorch/ovladači; nejsou zde ověřeny.

LTX používá šířku/výšku v násobcích 32 a počet snímků `8n+1` (např. 25, 49, 81). Přibližná délka exportu = počet snímků / FPS. Výchozích 25 snímků při 24 FPS je přibližně 1,04 s. Audio prompt i obrazové prompty doporučujeme psát anglicky; offline překladač není součástí aplikace.

## Offline režim a modelové soubory

Generovací proces před importem knihoven nastavuje `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, vypíná HF telemetry a načítá `local_files_only=True`. Stahování je samostatná explicitní akce. Aplikace nepoužívá vzdálené generovací API. Pro silné oddělení od sítě můžete po instalaci síť zcela odpojit; model musí být kompletně připravený.

Stažení modelu je označeno jako hotové až po úspěšném návratu downloaderu. Přerušené stažení lze spustit znovu. Downloader vybírá Diffusers komponenty, nikoli všechny jednotlivé checkpointy v repozitáři. Úplnost jednotlivých komponent se definitivně ověřuje při načítání pipeline. HF repozitáře se mohou měnit; aplikace v této verzi nepřipíná konkrétní revize vah.

Modely a nastavení se ukládají mimo zdrojový projekt:

- Windows: `%LOCALAPPDATA%\LocalAiGenerator`
- macOS: `~/Library/Application Support/LocalAiGenerator`
- Linux: `~/.local/share/local-ai-generator` (respektuje `XDG_DATA_HOME`)
- Volitelný vlastní adresář: proměnná `LOCALAIGENERATOR_HOME`.

Přenos na počítač bez sítě: nejprve na připojeném počítači nainstalujte knihovny a stáhněte váhy; kompletní modelovou složku přeneste a zvolte ji v aplikaci. Knihovny na cílovém OS instalujte z odpovídajících předem stažených wheelů. Pokud model vyžaduje autorizaci, použijte Hugging Face CLI v prostředí projektu (`hf auth login`) nebo importujte už staženou oprávněně získanou složku. GUI vlastní login neposkytuje.

Zastavení ukončí pracovní proces. Může zůstat prázdná úlohová složka nebo soubor `pending`; aplikace ho neoznačí jako hotový výsledek. Výstupní JSON obsahuje také prompt a lokální cesty, proto jej před sdílením zkontrolujte.

## Licence modelů a projektu

Veřejný repozitář automaticky neznamená právo ke komerčnímu použití každého modelu. Váhy nejsou redistribuované a licence modelu není licence aplikace.

- [SD 1.5](https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5)
- [SDXL Base](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0)
- [SDXL Turbo](https://huggingface.co/stabilityai/sdxl-turbo)
- [LTX Video](https://huggingface.co/Lightricks/LTX-Video)
- [AudioLDM 2](https://huggingface.co/cvssp/audioldm2): karta uvádí **CC-BY-NC-SA-4.0**, tedy nekomerční použití.

Projektová licence zatím není zvolená; viz `LICENSE-NOTICE.md`. Závislosti mají vlastní licence. PySide6/Qt nabízí LGPL/GPL a komerční licencování; při budoucí distribuci zabalených binárek zachovejte příslušná licenční oznámení a podmínky. Toto vydání distribuuje zdrojový projekt, nikoli zabalený Qt/PyTorch runtime nebo modelové váhy.

## Vývoj a testování

```bash
python -m unittest discover -s tests -v
python -m compileall -q localaigenerator start.py setup_ai.py
```

Testy jádra nepotřebují PyTorch, váhy ani síť. Ověřují validaci, výběr backendu, přerušené stahování a exportní cesty s náhradami AI knihoven. Neprokazují kvalitu reálného modelu ani jeho funkčnost na všech GPU. Volitelný GUI smoke test: `QT_QPA_PLATFORM=offscreen python tests/gui_smoke.py` po instalaci GUI.

GitHub Actions je připraven pro Windows/macOS/Linux a Python 3.10/3.12. Workflow není spuštěné, dokud projekt není v repozitáři. Před stabilním veřejným vydáním je potřeba reálné generování s každým vybraným modelem a kontrola instalace na cílových systémech.

## GitHub repozitář

Projekt je vyvíjen v soukromém repozitáři [jproucil-byte/local-ai-generator](https://github.com/jproucil-byte/local-ai-generator). Název aplikace je **Local Ai Generator**; název repozitáře se může lišit.

```bash
git clone https://github.com/jproucil-byte/local-ai-generator.git
cd local-ai-generator
python start.py
```

Pro soukromý repozitář je potřeba přihlášení s oprávněním číst jeho obsah. Veřejnost repozitáře lze změnit později v jeho nastavení. Modelové váhy, `.venv`, osobní nastavení a výstupy do GitHubu nepatří.
