
> ⚠️ **DO NOT USE THIS FRAMEWORK TO CHEAT** ⚠️
>
> This project is for educational and experimental purposes only. Using this framework to gain an unfair advantage in GeoGuessr or any other game violates its terms of service and goes against the spirit of fair play.

Autonomous framework using browser automation to allow large language models to play GeoGuessr.

# Setup
1. `pip install -r requirements.txt`
2. Add `GEMINI_API_KEY` to .env
3. Change `EDGE_USER_DATA_DIR` and `MSEDGEDRIVER_PATH` as necessary in `config.py` (replace USERNAME)
4. `python bot.py`

# Duel loop
1. Once a duel has been started, the loop begins by detecting relevant UI elements and either storing their value or removing them from display (e.g. HP bars).
2. A screenshot is taken and immediately given as a prompt, alongside the text of the system prompt, to the configured LLM.
3. The guess given back by the LLM is then parsed.


This suite currently supports **No Moving, Panning or Zooming** only, with eventual support for **No Moving**. Gemini 2.0 Flash, Gemini 2.5 Flash, and Gemini 2.5 Pro are supported. The nature of duels makes Gemini 2.5 Pro a poor choice despite its ability, due to its latency.