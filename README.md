# LBI Network Medicine Poster Template

LaTeX poster template for the [Ludwig Boltzmann Institute for Network Medicine at the University of Vienna](https://netmed.lbg.ac.at/) (LBI-NetMed). It is based on the [JRC ISIA poster template](https://git.isia.fh-salzburg.ac.at/publications/templates/isia-poster-template), a fork of the [Gemini](https://github.com/anishathalye/gemini) beamerposter theme.

The default layout is A0 portrait with two columns; landscape and other paper sizes work too.

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

## Logos

All logos are vector PDFs converted from the official SVG files with Inkscape:

```
inkscape --export-type=pdf --export-area-drawing --export-filename=<out>.pdf <in>.svg
```

| File | Source |
|---|---|
| `logos/lbi-netmed.pdf` | LBI-NetMed logo `LBI_NetMed_EN_Basisfarben.svg` (netmed.lbg.ac.at) |
| `logos/partners/univie.pdf` | University of Vienna logo `univie.svg` (univie.ac.at) |
| `logos/partners/vbc.pdf` | Vienna BioCenter logo `VBC_LOGO_rgb.svg` (viennabiocenter.org → About → Downloads) |
| `logos/partners/cemm.pdf` | CeMM logo `footer-logo.svg` (cemm.at) |

## Maintainer

- simon@lbi-netmed.com

## License

The Gemini theme is copyright (c) 2018-2022 Anish Athalye and released under the MIT License; see [LICENSE.md](LICENSE.md). The logos belong to their respective institutions.
