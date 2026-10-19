# LBI Network Medicine Poster Template

LaTeX poster template for the [Ludwig Boltzmann Institute for Network Medicine at the University of Vienna](https://netmed.lbg.ac.at/) (LBI-NetMed). It is based on the [JRC ISIA poster template](https://git.isia.fh-salzburg.ac.at/publications/templates/isia-poster-template), a fork of the [Gemini](https://github.com/anishathalye/gemini) beamerposter theme.

The default layout is A0 portrait with two columns; landscape and other paper sizes work too.

The template comes in two editions with the same look: the LaTeX template described below, and Inkscape templates for people who don't use LaTeX (see [Using Inkscape](#using-inkscape)).

## Dependencies

- A TeX installation with LuaLaTeX and `latexmk`, e.g. TeX Live 2025
- The `beamerposter` package and the fonts Source Sans Pro and Source Serif Pro (all part of a full TeX Live installation)

## Usage

1. Copy the files in this repository (or clone it).
2. Edit `poster_template.tex`: title, authors, institutes, footer, and the poster content.
3. Run `latexmk` to build `poster_template.pdf`.

PDFs in the top-level folder are git-ignored, because that is where the poster is built; keep PDF figures in a subfolder such as `figures/`.

### Paper size and columns

Set the paper in the `beamerposter` line of `poster_template.tex`, e.g. `orientation=landscape` or `size=a1`. For N columns, choose `\sepwidth` and `\colwidth` such that (N+1)·`\sepwidth` + N·`\colwidth` = `\paperwidth`; for three columns, use `0.025\paperwidth` and `0.3\paperwidth`, and add a third `column` environment.

### Header

`\logoleft{...}` puts a logo to the left of the title block (the demo uses the LBI logo); `\logoright{...}` adds an optional logo on the right. Both take any content, typically `\includegraphics[height=...]{...}`. The title, authors, and institutes come from `\title`, `\author`, and `\institute`.

### Footer

`\footercontent{...}` sets the footer text and `\footerlogos{...}` the partner logos shown right-aligned next to it. Both are optional; leave both out to remove the footer.

```latex
\footerlogos{%
    \includegraphics[height=2.8cm]{logos/partners/univie}\hspace{4ex}%
    \includegraphics[height=3.6cm]{logos/partners/vbc}\hspace{4ex}%
    \includegraphics[height=3.2cm]{logos/partners/cemm}}
```

### Blocks and colors

Use `block`, `alertblock` (blue), and `exampleblock` (mauve); `\heading{...}` adds a sub-heading inside a block. The color theme `beamercolorthemelbi.sty` defines `lbiblue` (#004A99), `lbimauve` (#B9AEBB), and `lbinavy` (#001242), which you can also use in figures, e.g. `\addplot[lbiblue]`.

## Using Inkscape

The `inkscape/` folder holds the same poster as editable Inkscape templates:

| Template | Paper | Columns |
|---|---|---|
| `inkscape/lbi-poster-a0-portrait.svg` | A0 portrait | 2 |
| `inkscape/lbi-poster-a0-landscape.svg` | A0 landscape | 3 |
| `inkscape/lbi-poster-a1-portrait.svg` | A1 portrait | 2 |

1. **Install the fonts once** from `inkscape/fonts/` (Source Sans Pro and Source Serif Pro). On macOS, double-click each `.otf` file ▸ Install. On Windows, right-click ▸ Install. On Linux, copy them to `~/.local/share/fonts`. Restart Inkscape afterwards.
2. **Open a template in Inkscape 1.2 or newer.** Older versions show the block text unwrapped. Use File ▸ Save As right away to save your own copy.
3. **Edit it** (see below).
4. **Export it** with File ▸ Save a Copy ▸ PDF, with "Embed fonts" selected, and print that PDF.

**Layers.** The template has three layers (Layer ▸ Layers and Objects):
- `Branding` holds the LBI logo, the blue header and footer rules, and the University of Vienna logo in the footer.
  - **Logos:** you can move, resize or delete them. To keep a logo's proportions while resizing, hold Ctrl as you drag a corner arrow. The Vienna BioCenter and CeMM logos are in `logos/svg/`; add them with File ▸ Import.
  - **Rules:** each rule is locked so it doesn't move by accident. To move one, for example the header rule below a taller header, unlock it with the lock icon next to it in the Layers and Objects panel.
- `Header & footer text` holds the title, authors, affiliations and contact line.
- `Content` holds the blocks and figures.

**Editing blocks.** Every block is a group made of a title, a blue rule or colored bar, and a text frame.
- Double-click the text to edit it; it wraps inside its frame.
- To make a block taller or shorter, don't drag the arrows around a selected block: that stretches the whole block, text included. Instead, pick the Text tool (T), click into the block's text, and drag the small square handle at the lower right corner of its frame; the text rewraps. In alert and example blocks this also resizes the tinted background, which is the frame.
- A red frame outline means the text doesn't fit and the rest is hidden. Make the frame taller or shorten the text.
- To add a block, select an existing one, press Ctrl+D to duplicate it, and move the copy. The copy gets its own frame.
- Blue guides mark the columns. Objects snap to them only when snapping is on: click the magnet button at the top right of the window (or press %). If objects still don't snap to the guides, open the snapping menu next to the magnet, switch to Advanced mode, and tick Guides.

**Bullets.** List lines start with a blue ▴. To add one, copy an existing bullet line, or type it in the Text tool with Ctrl+U, `25b4`, Enter, and color it with the `lbiblue` swatch.

**Figures.** Use File ▸ Import (Ctrl+I) to add PNG, JPG, SVG or PDF figures, place them in a column, and delete the dashed placeholder. SVG and PDF figures stay sharp at poster size.

**Colors.** The LBI colors (`lbiblue`, `lbimauve`, `lbinavy`, and the light tints the blocks use) are stored in each template as document swatches. They don't appear in the color bar at the bottom of the window until you choose "Document swatches" in that bar's palette menu. You can also open Object ▸ Swatches (Ctrl+Shift+W) and choose "Document swatches" there.

**Missing fonts.** Without the fonts installed, Inkscape silently uses another font, and the font name in the Text toolbar appears struck through in red. Install the fonts (step 1) and reopen the file.

The Inkscape edition has no equation typesetting, automatic figure numbering or bibliography: type references as text, and paste equations as images.

## Logos

The official SVG files are in `logos/svg/`. The LaTeX edition uses vector PDFs converted from them with Inkscape:

```
inkscape --export-type=pdf --export-area-drawing --export-filename=<out>.pdf <in>.svg
```

| File | Source |
|---|---|
| `logos/lbi-netmed.pdf` | LBI-NetMed logo `LBI_NetMed_EN_Basisfarben.svg` (netmed.lbg.ac.at) |
| `logos/partners/univie.pdf` | University of Vienna logo `univie.svg` (univie.ac.at) |
| `logos/partners/vbc.pdf` | Vienna BioCenter logo `VBC_LOGO_rgb.svg` (viennabiocenter.org → About → Downloads) |
| `logos/partners/cemm.pdf` | CeMM logo `footer-logo.svg` (cemm.at) |

## Maintainers

- `python3 tools/make_inkscape_templates.py` regenerates the three templates in `inkscape/` from `beamercolorthemelbi.sty`, `logos/svg/`, and the fonts in `inkscape/fonts/`. Unchanged inputs give byte-identical output; commit the regenerated files.
- `python3 -m unittest discover -s tools` runs the generator's tests.
- The Inkscape footer shows the logos listed in `FOOTER_LOGOS` in `tools/make_inkscape_templates.py`, and its rule and text move with the tallest one, as in LaTeX. When you change `\footerlogos` in `poster_template.tex`, update `FOOTER_LOGOS` to match and regenerate the templates.
- To replace a logo:
  1. Put the new SVG in `logos/svg/`.
  2. Convert it to the PDF the LaTeX edition uses with the Inkscape command above, e.g. `inkscape --export-type=pdf --export-area-drawing --export-filename=logos/partners/vbc.pdf logos/svg/vbc.svg`.
  3. Update its drawing box in `LOGO_BOXES` in `tools/make_inkscape_templates.py`, measured with `inkscape --query-x --query-y --query-width --query-height logos/svg/<name>.svg`.
  4. Regenerate the templates.

## Maintainer

- simon@lbi-netmed.com

## License

The Gemini theme is copyright (c) 2018-2022 Anish Athalye and released under the MIT License; see [LICENSE.md](LICENSE.md). The logos belong to their respective institutions. The fonts in `inkscape/fonts/` (Source Sans Pro, Source Serif Pro) are by Adobe and released under the SIL Open Font License 1.1; see the license files in that folder.
