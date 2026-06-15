# How to run LatticeFlow EDM site

## Quick start (Windows)

1. Go to folder: `lattice PROJECT`
2. **Double-click** `RUN_SITE.bat`
3. Wait until you see: `LatticeFlow EDM → http://localhost:5000`
4. Browser opens automatically — if not, open **http://localhost:5000** yourself
5. **Keep the black terminal window open** while using the site

---

## If you see the OLD dark UI

You may see text like *"Enter every parameter manually — nothing is pre-selected"* in a dark theme.

That is the **old cached page**. Fix:

1. Close the browser tab
2. In the terminal, press **Ctrl+C** to stop the server
3. Run **`RUN_SITE.bat`** again
4. In browser press **Ctrl + Shift + R** (hard refresh)

**New UI looks like:** white background, "Lattice machining analysis" title, left config panel + right results panel.

---

## Manual run (if bat file fails)

Open **PowerShell** or **Command Prompt**:

```powershell
cd "c:\Users\raj shekhar\Downloads\lattice PROJECT"
pip install -r requirements.txt
python web_server.py
```

Then open: **http://localhost:5000**

---

## Do NOT use these (wrong app)

| Wrong | Right |
|-------|-------|
| `streamlit run app.py` | `python web_server.py` or `RUN_SITE.bat` |
| Opening `index.html` directly in browser | Use **http://localhost:5000** |
| Old tab left open for days | Hard refresh **Ctrl+Shift+R** |

---

## How to use the site

1. **Enter manually** (nothing pre-filled):
   - Peak current (A), Pulse-on (µs), Duty (%)
   - Tool diameter (400–1500 µm dropdown)
   - Pore diameter (µm), Working area (µm)
   - Tool position X, Y (µm)

2. Click **Run analysis**

3. Results appear on the **right** — circularity score, PASS/FAIL, lattice image

4. Click **Open detailed engineering report** for full PDF-style report

5. Optional: **Grid scan** — tests all positions in the working area

---

## Deploy online (Render + GitHub)

1. Push this folder to GitHub
2. Create account on [render.com](https://render.com)
3. New → Web Service → connect your repo
4. Render uses `render.yaml` automatically
5. Your public URL: `https://your-app-name.onrender.com`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Cannot reach server" | Run `RUN_SITE.bat`, keep terminal open |
| Old dark UI | Ctrl+Shift+R, restart `RUN_SITE.bat` |
| Tool dropdown empty | Hard refresh; use port 5000 not Streamlit |
| Port already in use | `RUN_SITE.bat` kills old process automatically |
